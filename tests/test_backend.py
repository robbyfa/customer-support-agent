"""Real checkpoint/HTTP integration; only expensive upstream nodes are stubbed."""

import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.api import create_app
from backend.service import CaseService, DecisionConflict
from graph.graph import build_graph
from graph.nodes.approval_gate import ReviewDecision


@pytest.fixture
def graph_factory(monkeypatch):
    import graph.graph as module

    calls = []

    def classify(state):
        calls.append("classify")
        return {"classification": {
            "category": "other", "sensitive_case": "sensitive" in state["customer_message"],
        }}

    def draft(state):
        calls.append("draft")
        return {"draft_response": {
            "customer_message": "We will review your request.",
            "approval_required": state["customer_message"] != "safe",
        }}

    monkeypatch.setattr(module, "classify_ticket", classify)
    monkeypatch.setattr(module, "retrieve_policy", lambda state: {"policy_context": ["policy"]})
    monkeypatch.setattr(module, "get_customer_context", lambda state: {"customer_context": {
        "profile": {"name": "Jane Smith", "email": "jane@example.com"},
    }})
    monkeypatch.setattr(module, "generate_resolution_plan", draft)
    monkeypatch.setattr(module, "groundedness_check", lambda state: {
        "groundedness_check": {"is_grounded": True},
    })
    return build_graph, calls


@asynccontextmanager
async def open_service(path, factory):
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        await saver.setup()
        yield CaseService(factory(saver))


@pytest.mark.parametrize("approved", [True, False])
def test_restart_resume_and_idempotency(tmp_path, graph_factory, approved):
    factory, calls = graph_factory
    path = tmp_path / "restart.sqlite"

    async def start():
        async with open_service(path, factory) as service:
            case = await service.create("review please", "CUST-1001")
            assert case["status"] == "pending_review"
            assert case["final_output"] is None
            assert case["preview"]["approved"] is None
            assert case["preview"]["customer_context"]["profile"]["email"] == "j***@example.com"
            assert not any(e["step"] in {"approval_gate", "audit_log", "final_response"} for e in case["audit_trail"])
            return case["id"]

    case_id = asyncio.run(start())  # Close the DB and event loop, just like process shutdown.

    async def resume():
        async with open_service(path, factory) as service:
            assert (await service.get(case_id))["status"] == "pending_review"
            decision = ReviewDecision(approved=approved, reviewer="Agent A", reason="Reviewed policy")
            case = await service.decide(case_id, decision)
            assert case["status"] == ("approved" if approved else "rejected")
            assert case["final_output"]["approved"] is approved
            assert (await service.decide(case_id, decision)) == case
            with pytest.raises(DecisionConflict):
                await service.decide(case_id, decision.model_copy(update={"approved": not approved}))
            entries = [e for e in case["audit_trail"] if e["step"] == "approval_gate"]
            assert len(entries) == 1
            assert entries[0]["reviewer"] == "Agent A"
            return case

    completed = asyncio.run(resume())
    assert calls == ["classify", "draft"]  # Upstream generation wasn't replayed.

    async def reload():
        async with open_service(path, factory) as service:
            assert await service.get(case_id) == completed
    asyncio.run(reload())


def test_auto_approval_and_concurrent_conflict(tmp_path, graph_factory):
    factory, _ = graph_factory

    async def run():
        async with open_service(tmp_path / "cases.sqlite", factory) as service:
            safe = await service.create("safe", None)
            assert safe["status"] == "approved"
            case = await service.create("sensitive", None)
            results = await asyncio.gather(*[
                service.decide(case["id"], ReviewDecision(approved=choice, reviewer="A", reason="Reviewed"))
                for choice in (True, False)
            ], return_exceptions=True)
            assert sum(isinstance(result, DecisionConflict) for result in results) == 1
            assert (await service.get(safe["id"])) == safe
    asyncio.run(run())


def test_http_contract(tmp_path, graph_factory):
    factory, _ = graph_factory

    async def run():
        async with open_service(tmp_path / "http.sqlite", factory) as service:
            api = create_app(service)
            async with (
                api.router.lifespan_context(api),
                httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url="http://test") as client,
            ):
                assert (await client.get("/health")).status_code == 200
                assert (await client.post("/cases", json={"customer_message": "  "})).status_code == 422
                assert (await client.get(f"/cases/{uuid4()}")).status_code == 404
                assert (await client.get("/cases/invalid")).status_code == 422
                created = await client.post("/cases", json={"customer_message": "review please"})
                assert created.status_code == 201
                case = created.json()
                url = f"/cases/{case['id']}"
                assert (await client.get(url)).json() == case
                assert (await client.post(url + "/approve", json={})).status_code == 422
                body = {"reviewer": "A", "reason": "Needs specialist"}
                rejected = await client.post(url + "/reject", json=body)
                assert rejected.json()["status"] == "rejected"
                assert (await client.post(url + "/reject", json=body)).json() == rejected.json()
                assert (await client.post(url + "/approve", json=body)).status_code == 409
                audit = (await client.get(url + "/audit")).json()["audit_trail"]
                assert audit[-1]["status"] == "rejected"
    asyncio.run(run())


def test_graph_failure_is_readable_after_restart(tmp_path, graph_factory, monkeypatch):
    import graph.graph as module
    factory, _ = graph_factory

    def fail(state):
        raise RuntimeError("secret provider detail")

    monkeypatch.setattr(module, "generate_resolution_plan", fail)
    path = tmp_path / "failed.sqlite"

    async def run():
        async with open_service(path, factory) as service:
            case = await service.create("review please", None)
            assert case["status"] == "failed"
            assert "secret provider detail" not in str(case)
            return case["id"]
    case_id = asyncio.run(run())

    async def reload():
        async with open_service(path, factory) as service:
            assert (await service.get(case_id))["status"] == "failed"
    asyncio.run(reload())


def test_groundedness_exhaustion_still_requires_review(tmp_path, graph_factory, monkeypatch):
    import graph.graph as module
    from graph.nodes.groundedness_check import MAX_RETRIES

    factory, calls = graph_factory
    monkeypatch.setattr(module, "groundedness_check", lambda state: {
        "groundedness_check": {"is_grounded": False, "issues": ["Unsupported claim"]},
        "draft_retries": state.get("draft_retries", 0) + 1,
    })

    async def run():
        async with open_service(tmp_path / "fallback.sqlite", factory) as service:
            case = await service.create("safe", None)
            assert case["status"] == "pending_review"
            assert case["final_output"] is None
            assert case["preview"]["draft_response"]["approval_required"] is True
            assert any(entry["step"] == "manual_review_response" for entry in case["audit_trail"])
            assert calls.count("draft") == MAX_RETRIES
    asyncio.run(run())
