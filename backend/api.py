"""Run with: uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000."""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, ConfigDict, Field

from backend.service import CaseNotFound, CaseService, DecisionConflict
from graph.graph import build_graph
from graph.nodes.approval_gate import ReviewDecision

load_dotenv()


class NewCase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    customer_message: str = Field(min_length=1, max_length=10000)
    customer_id: str | None = Field(default=None, pattern=r"^CUST-\d{4}$")


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    reviewer: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)


class CaseResponse(BaseModel):
    id: UUID
    status: Literal["running", "failed", "pending_review", "approved", "rejected"]
    review_decision: ReviewDecision | None = None
    final_output: dict[str, Any] | None = None
    preview: dict[str, Any]
    groundedness_check: dict[str, Any] | None = None
    audit_trail: list[dict[str, Any]]


class AuditResponse(BaseModel):
    id: UUID
    status: Literal["running", "failed", "pending_review", "approved", "rejected"]
    audit_trail: list[dict[str, Any]]


def setup_tools():
    from storage.vector_store import PolicyVectorStore
    from tools.registry import configure

    store = PolicyVectorStore(collection_name="copilot_api")
    store.ingest_policies()
    configure(store)


def create_app(service=None):
    @asynccontextmanager
    async def lifespan(application):
        if service is not None:
            application.state.cases = service
            yield
            return
        path = Path(os.getenv("CHECKPOINT_DB", "runtime/checkpoints.sqlite"))
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(setup_tools)
        async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
            await saver.setup()
            application.state.cases = CaseService(build_graph(saver))
            yield

    application = FastAPI(title="Customer Support Resolution Copilot", lifespan=lifespan)

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    @application.post("/cases", status_code=201, response_model=CaseResponse)
    async def create_case(body: NewCase):
        return await application.state.cases.create(body.customer_message, body.customer_id)

    async def get_case_or_404(case_id):
        try:
            return await application.state.cases.get(str(case_id))
        except CaseNotFound:
            raise HTTPException(404, "Case not found") from None

    @application.get("/cases/{case_id}", response_model=CaseResponse)
    async def get_case(case_id: UUID):
        return await get_case_or_404(case_id)

    @application.get("/cases/{case_id}/audit", response_model=AuditResponse)
    async def audit(case_id: UUID):
        case = await get_case_or_404(case_id)
        return {"id": case["id"], "status": case["status"], "audit_trail": case["audit_trail"]}

    async def decide(case_id, body, approved):
        try:
            return await application.state.cases.decide(
                str(case_id), ReviewDecision(approved=approved, **body.model_dump())
            )
        except CaseNotFound:
            raise HTTPException(404, "Case not found") from None
        except DecisionConflict as exc:
            raise HTTPException(409, str(exc)) from None

    @application.post("/cases/{case_id}/approve", response_model=CaseResponse)
    async def approve(case_id: UUID, body: ReviewRequest):
        return await decide(case_id, body, True)

    @application.post("/cases/{case_id}/reject", response_model=CaseResponse)
    async def reject(case_id: UUID, body: ReviewRequest):
        return await decide(case_id, body, False)

    return application


app = create_app()
