"""Integration tests for graph nodes and chains.

Tests marked with @pytest.mark.llm require OPENAI_API_KEY to be set.
Run with: uv run pytest tests/test_graph.py -v -m llm
Skip LLM tests: uv run pytest tests/test_graph.py -v -m "not llm"
"""

import os

import pytest

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

llm = pytest.mark.llm
requires_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


# ---------------------------------------------------------------------------
# classify_ticket node
# ---------------------------------------------------------------------------


@requires_api_key
@llm
class TestClassifyTicketNode:
    def test_failed_withdrawal(self):
        from graph.nodes.classify_ticket import classify_ticket

        state = {
            "customer_message": (
                "I tried to withdraw €300 three times and it keeps failing. "
                "Nobody is helping me."
            ),
            "audit_trail": [],
        }
        result = classify_ticket(state)

        assert "classification" in result
        c = result["classification"]
        assert c["category"] == "withdrawal_issue"
        assert c["urgency"] == "high"
        assert c["sentiment"] == "negative"
        assert c["requires_human_review"] is True
        assert isinstance(c["summary"], str) and len(c["summary"]) > 0

    def test_login_issue(self):
        from graph.nodes.classify_ticket import classify_ticket

        state = {
            "customer_message": (
                "I can't log in to my account. It says my account is locked."
            ),
            "audit_trail": [],
        }
        result = classify_ticket(state)
        c = result["classification"]
        assert c["category"] == "login_issue"

    def test_responsible_gaming(self):
        from graph.nodes.classify_ticket import classify_ticket

        state = {
            "customer_message": (
                "I want to set a self-exclusion period. "
                "I need to take a break from gambling."
            ),
            "audit_trail": [],
        }
        result = classify_ticket(state)
        c = result["classification"]
        assert c["category"] == "responsible_gaming"
        assert c["sensitive_case"] is True

    def test_customer_id_extraction(self):
        from graph.nodes.classify_ticket import classify_ticket

        state = {
            "customer_message": (
                "My customer ID is CUST-1001 and my withdrawal keeps failing."
            ),
            "audit_trail": [],
        }
        result = classify_ticket(state)
        assert result["customer_id"] == "CUST-1001"

    def test_customer_id_fallback_to_state(self):
        from graph.nodes.classify_ticket import classify_ticket

        state = {
            "customer_message": "My withdrawal keeps failing.",
            "customer_id": "CUST-1002",
            "audit_trail": [],
        }
        result = classify_ticket(state)
        # No ID in message, should fall back to state
        assert result["customer_id"] == "CUST-1002"

    def test_audit_trail_appended(self):
        from graph.nodes.classify_ticket import classify_ticket

        state = {
            "customer_message": "I have a question about my bonus.",
            "audit_trail": [{"step": "previous_step"}],
        }
        result = classify_ticket(state)
        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[0]["step"] == "previous_step"
        assert trail[1]["step"] == "classify_ticket"
        assert "timestamp" in trail[1]
        assert "category" in trail[1]


# ===========================================================================
# customer_context node tests (Task 7)
# ===========================================================================

from graph.nodes.customer_context import get_customer_context


class TestCustomerContextNode:
    def test_cust_1001_has_three_failed_withdrawals(self):
        state = {"customer_id": "CUST-1001", "audit_trail": []}
        result = get_customer_context(state)

        ctx = result["customer_context"]
        assert "error" not in ctx
        assert ctx["flags"]["failed_withdrawal_count"] == 3
        assert ctx["flags"]["has_failed_withdrawals"] is True
        assert len(ctx["transactions"]) == 5
        assert len(ctx["tickets"]) == 3

    def test_cust_1003_account_locked(self):
        state = {"customer_id": "CUST-1003", "audit_trail": []}
        result = get_customer_context(state)

        ctx = result["customer_context"]
        assert ctx["flags"]["account_locked"] is True

    def test_cust_1004_has_active_bonus(self):
        state = {"customer_id": "CUST-1004", "audit_trail": []}
        result = get_customer_context(state)

        ctx = result["customer_context"]
        assert ctx["flags"]["has_active_bonus"] is True
        assert len(ctx["bonuses"]) == 1

    def test_cust_1005_verification_pending(self):
        state = {"customer_id": "CUST-1005", "audit_trail": []}
        result = get_customer_context(state)

        ctx = result["customer_context"]
        assert ctx["flags"]["verification_pending"] is True

    def test_cust_1006_responsible_gaming_flag(self):
        state = {"customer_id": "CUST-1006", "audit_trail": []}
        result = get_customer_context(state)

        ctx = result["customer_context"]
        assert ctx["flags"]["responsible_gaming_flag"] is True

    def test_empty_customer_id_returns_error(self):
        state = {"customer_id": "", "audit_trail": []}
        result = get_customer_context(state)

        assert "error" in result["customer_context"]

    def test_no_customer_id_returns_error(self):
        state = {"audit_trail": []}
        result = get_customer_context(state)

        assert "error" in result["customer_context"]

    def test_unknown_customer_returns_error(self):
        state = {"customer_id": "CUST-9999", "audit_trail": []}
        result = get_customer_context(state)

        assert "error" in result["customer_context"]

    def test_audit_trail_appended(self):
        state = {
            "customer_id": "CUST-1001",
            "audit_trail": [{"step": "classify_ticket"}],
        }
        result = get_customer_context(state)

        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "customer_context"
        assert trail[1]["customer_id"] == "CUST-1001"

    def test_context_has_expected_keys(self):
        state = {"customer_id": "CUST-1002", "audit_trail": []}
        result = get_customer_context(state)

        ctx = result["customer_context"]
        assert "profile" in ctx
        assert "transactions" in ctx
        assert "tickets" in ctx
        assert "bonuses" in ctx
        assert "flags" in ctx


# ===========================================================================
# draft_response node tests (Task 9)
# ===========================================================================

from graph.nodes.draft_response import draft_response


@requires_api_key
@llm
class TestDraftResponseNode:
    def test_high_risk_withdrawal_requires_approval(self):
        state = {
            "customer_message": "I tried to withdraw €300 three times and it keeps failing.",
            "classification": {
                "category": "withdrawal_issue",
                "urgency": "high",
                "sentiment": "negative",
                "summary": "Customer reports 3 failed withdrawals.",
                "requires_human_review": True,
                "sensitive_case": False,
            },
            "policy_context": [
                "Repeated failed withdrawals must be treated as high priority. "
                "Support agents must not tell the customer that the withdrawal "
                "is resolved unless payment status has been confirmed."
            ],
            "customer_context": {
                "profile": {"customer_id": "CUST-1001", "name": "Maria Gonzalez"},
                "flags": {"failed_withdrawal_count": 3},
            },
            "risk_assessment": {
                "risk_level": "high",
                "requires_human_review": True,
                "risk_factors": ["3 failed withdrawals"],
            },
            "audit_trail": [],
        }
        result = draft_response(state)

        assert "draft_response" in result
        assert "recommendation" in result
        dr = result["draft_response"]
        assert dr["approval_required"] is True
        assert dr["tone"] in ("empathetic", "formal")

    def test_low_risk_returns_draft(self):
        state = {
            "customer_message": "When will my deposit show up?",
            "classification": {
                "category": "deposit_issue",
                "urgency": "medium",
                "sentiment": "neutral",
                "summary": "Customer asks about deposit timing.",
                "requires_human_review": False,
                "sensitive_case": False,
            },
            "policy_context": [
                "Bank transfer deposits take 1-3 business days."
            ],
            "customer_context": {
                "profile": {"customer_id": "CUST-1002", "name": "James O'Brien"},
                "flags": {},
            },
            "risk_assessment": {
                "risk_level": "low",
                "requires_human_review": False,
                "risk_factors": [],
            },
            "audit_trail": [],
        }
        result = draft_response(state)

        dr = result["draft_response"]
        assert isinstance(dr["customer_message"], str)
        assert len(dr["customer_message"]) > 0

    def test_audit_trail_appended(self):
        state = {
            "customer_message": "I have a bonus question.",
            "classification": {"category": "bonus_issue", "urgency": "low", "sentiment": "neutral"},
            "policy_context": ["Wagering requirements must be met."],
            "customer_context": {"profile": {}, "flags": {}},
            "risk_assessment": {"risk_level": "low", "requires_human_review": False},
            "audit_trail": [{"step": "risk_check"}],
        }
        result = draft_response(state)

        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "draft_response"
        assert "tone" in trail[1]


# ===========================================================================
# approval_gate and final_response node tests (Task 10)
# ===========================================================================

from graph.nodes.approval_gate import approval_gate
from graph.nodes.final_response import final_response


class TestApprovalGateNode:
    def test_risk_requires_review_not_approved(self):
        state = {
            "risk_assessment": {"requires_human_review": True},
            "draft_response": {"approval_required": False},
            "classification": {"sensitive_case": False},
            "audit_trail": [],
        }
        result = approval_gate(state)
        assert result["approved"] is False

    def test_draft_requires_approval_not_approved(self):
        state = {
            "risk_assessment": {"requires_human_review": False},
            "draft_response": {"approval_required": True},
            "classification": {"sensitive_case": False},
            "audit_trail": [],
        }
        result = approval_gate(state)
        assert result["approved"] is False

    def test_sensitive_case_not_approved(self):
        state = {
            "risk_assessment": {"requires_human_review": False},
            "draft_response": {"approval_required": False},
            "classification": {"sensitive_case": True},
            "audit_trail": [],
        }
        result = approval_gate(state)
        assert result["approved"] is False

    def test_no_review_needed_approved(self):
        state = {
            "risk_assessment": {"requires_human_review": False},
            "draft_response": {"approval_required": False},
            "classification": {"sensitive_case": False},
            "audit_trail": [],
        }
        result = approval_gate(state)
        assert result["approved"] is True

    def test_audit_trail_appended(self):
        state = {
            "risk_assessment": {"requires_human_review": False},
            "draft_response": {"approval_required": False},
            "classification": {"sensitive_case": False},
            "audit_trail": [{"step": "draft_response"}],
        }
        result = approval_gate(state)
        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "approval_gate"
        assert "approved" in trail[1]
        assert "reason" in trail[1]


class TestFinalResponseNode:
    def test_approved_status(self):
        state = {
            "customer_message": "My withdrawal keeps failing.",
            "customer_id": "CUST-1001",
            "classification": {"category": "withdrawal_issue"},
            "policy_context": ["Withdrawal policy content"],
            "customer_context": {"profile": {"customer_id": "CUST-1001"}},
            "risk_assessment": {"risk_level": "high"},
            "recommendation": {"recommended_action": "Escalate"},
            "draft_response": {"customer_message": "We are investigating."},
            "approved": True,
            "audit_trail": [],
        }
        result = final_response(state)

        fo = result["final_output"]
        assert fo["status"] == "approved"
        assert fo["approved"] is True
        assert fo["customer_id"] == "CUST-1001"

    def test_pending_review_status(self):
        state = {
            "customer_message": "Self-exclusion request.",
            "customer_id": "CUST-1006",
            "classification": {"category": "responsible_gaming"},
            "policy_context": [],
            "customer_context": {},
            "risk_assessment": {"risk_level": "high"},
            "recommendation": {},
            "draft_response": {},
            "approved": False,
            "audit_trail": [],
        }
        result = final_response(state)

        fo = result["final_output"]
        assert fo["status"] == "pending_review"
        assert fo["approved"] is False

    def test_final_output_has_all_keys(self):
        state = {
            "customer_message": "Test",
            "customer_id": "CUST-1001",
            "classification": {},
            "policy_context": [],
            "customer_context": {},
            "risk_assessment": {},
            "recommendation": {},
            "draft_response": {},
            "approved": True,
            "audit_trail": [],
        }
        result = final_response(state)

        expected_keys = {
            "customer_message",
            "customer_id",
            "classification",
            "policy_context",
            "customer_context",
            "risk_assessment",
            "recommendation",
            "draft_response",
            "approved",
            "status",
        }
        assert expected_keys.issubset(result["final_output"].keys())

    def test_audit_trail_appended(self):
        state = {
            "customer_message": "Test",
            "approved": True,
            "audit_trail": [{"step": "approval_gate"}],
        }
        result = final_response(state)

        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "final_response"
        assert trail[1]["status"] == "approved"


# ===========================================================================
# End-to-end integration test (Task 11)
# ===========================================================================

from storage.vector_store import PolicyVectorStore
from tools.registry import configure as configure_registry


@requires_api_key
@llm
class TestEndToEndGraph:
    @pytest.fixture(autouse=True)
    def _setup_stores(self):
        """Ensure vector store is configured for the full graph run."""
        vs = PolicyVectorStore(collection_name="test_e2e")
        vs.ingest_policies()
        configure_registry(vs)

    def test_failed_withdrawal_full_run(self):
        from graph.graph import build_graph

        app = build_graph()
        result = app.invoke(
            {
                "customer_message": (
                    "I tried to withdraw €300 three times and it keeps failing. "
                    "Nobody is helping me."
                ),
                "customer_id": "CUST-1001",
                "audit_trail": [],
            }
        )

        # final_output should exist
        fo = result["final_output"]
        assert fo is not None

        # Classification
        assert fo["classification"]["category"] == "withdrawal_issue"
        assert fo["classification"]["urgency"] == "high"
        assert fo["classification"]["sentiment"] == "negative"

        # Policy context retrieved
        assert len(fo["policy_context"]) > 0

        # Customer context populated
        ctx = fo["customer_context"]
        assert "error" not in ctx
        assert ctx["flags"]["failed_withdrawal_count"] == 3

        # Risk assessment
        assert fo["risk_assessment"]["risk_level"] == "high"
        assert fo["risk_assessment"]["requires_human_review"] is True

        # Draft response exists
        assert fo["draft_response"]["customer_message"]
        assert fo["draft_response"]["tone"] in ("empathetic", "formal")

        # High-risk → not approved
        assert fo["approved"] is False
        assert fo["status"] == "pending_review"

        # Audit trail has entries for all 7 nodes
        trail = result["audit_trail"]
        steps = [e["step"] for e in trail]
        assert "classify_ticket" in steps
        assert "retrieve_policy" in steps
        assert "customer_context" in steps
        assert "risk_check" in steps
        assert "draft_response" in steps
        assert "approval_gate" in steps
        assert "final_response" in steps


# ===========================================================================
# Groundedness routing tests (no LLM needed)
# ===========================================================================

from graph.graph import _route_after_groundedness
from graph.consts import APPROVAL_GATE, DRAFT_RESPONSE, MANUAL_REVIEW_RESPONSE


class TestGroundednessRouting:
    def test_grounded_routes_to_approval(self):
        state = {
            "groundedness_check": {"is_grounded": True, "confidence": 0.95, "issues": []},
            "draft_retries": 0,
        }
        assert _route_after_groundedness(state) == APPROVAL_GATE

    def test_not_grounded_first_retry_routes_to_draft(self):
        state = {
            "groundedness_check": {"is_grounded": False, "confidence": 0.4, "issues": ["Unverified claim"]},
            "draft_retries": 0,
        }
        assert _route_after_groundedness(state) == DRAFT_RESPONSE

    def test_not_grounded_second_retry_routes_to_draft(self):
        state = {
            "groundedness_check": {"is_grounded": False, "confidence": 0.3, "issues": ["Still unverified"]},
            "draft_retries": 1,
        }
        assert _route_after_groundedness(state) == DRAFT_RESPONSE

    def test_not_grounded_max_retries_routes_to_manual_review(self):
        state = {
            "groundedness_check": {"is_grounded": False, "confidence": 0.2, "issues": ["Gave up"]},
            "draft_retries": 2,
        }
        assert _route_after_groundedness(state) == MANUAL_REVIEW_RESPONSE

    def test_missing_check_defaults_to_approval(self):
        state = {"draft_retries": 0}
        assert _route_after_groundedness(state) == APPROVAL_GATE


# ===========================================================================
# Conditional routing tests (Task 15 - updated for new graph)
# ===========================================================================

from graph.graph import route_by_category
from graph.consts import CUSTOMER_CONTEXT, MINIMAL_CUSTOMER_CONTEXT


class TestRouteByCategory:
    def test_responsible_gaming_routes_to_minimal_context(self):
        state = {"classification": {"category": "responsible_gaming"}}
        assert route_by_category(state) == MINIMAL_CUSTOMER_CONTEXT

    def test_withdrawal_routes_to_full_context(self):
        state = {"classification": {"category": "withdrawal_issue"}}
        assert route_by_category(state) == CUSTOMER_CONTEXT

    def test_deposit_routes_to_full_context(self):
        state = {"classification": {"category": "deposit_issue"}}
        assert route_by_category(state) == CUSTOMER_CONTEXT

    def test_login_routes_to_full_context(self):
        state = {"classification": {"category": "login_issue"}}
        assert route_by_category(state) == CUSTOMER_CONTEXT

    def test_bonus_routes_to_full_context(self):
        state = {"classification": {"category": "bonus_issue"}}
        assert route_by_category(state) == CUSTOMER_CONTEXT

    def test_other_routes_to_full_context(self):
        state = {"classification": {"category": "other"}}
        assert route_by_category(state) == CUSTOMER_CONTEXT

    def test_missing_classification_routes_to_full_context(self):
        state = {}
        assert route_by_category(state) == CUSTOMER_CONTEXT


# ===========================================================================
# New node tests: minimal_customer_context, manual_review, audit_log
# ===========================================================================

from graph.nodes.minimal_customer_context import get_minimal_customer_context
from graph.nodes.manual_review_response import manual_review_response
from graph.nodes.audit_log import audit_log as audit_log_node


class TestMinimalCustomerContext:
    def test_cust_1006_has_responsible_gaming_flag(self):
        state = {"customer_id": "CUST-1006", "audit_trail": []}
        result = get_minimal_customer_context(state)
        ctx = result["customer_context"]
        assert ctx["flags"]["responsible_gaming_flag"] is True
        assert ctx["transactions"] == []
        assert ctx["tickets"] == []
        assert ctx["bonuses"] == []

    def test_profile_included(self):
        state = {"customer_id": "CUST-1006", "audit_trail": []}
        result = get_minimal_customer_context(state)
        assert result["customer_context"]["profile"]["customer_id"] == "CUST-1006"

    def test_no_customer_id_returns_error(self):
        state = {"audit_trail": []}
        result = get_minimal_customer_context(state)
        assert "error" in result["customer_context"]

    def test_unknown_customer_returns_error(self):
        state = {"customer_id": "CUST-9999", "audit_trail": []}
        result = get_minimal_customer_context(state)
        assert "error" in result["customer_context"]

    def test_audit_trail_appended(self):
        state = {"customer_id": "CUST-1006", "audit_trail": [{"step": "retrieve_policy"}]}
        result = get_minimal_customer_context(state)
        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "minimal_customer_context"


class TestManualReviewResponse:
    def test_replaces_draft_with_template(self):
        state = {
            "classification": {"category": "withdrawal_issue"},
            "risk_assessment": {"risk_level": "high"},
            "audit_trail": [],
        }
        result = manual_review_response(state)
        draft = result["draft_response"]
        assert "flagged for review" in draft["customer_message"]
        assert draft["approval_required"] is True
        assert draft["tone"] == "formal"

    def test_audit_trail_appended(self):
        state = {
            "classification": {},
            "risk_assessment": {},
            "audit_trail": [{"step": "groundedness_check"}],
        }
        result = manual_review_response(state)
        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "manual_review_response"


class TestAuditLogNode:
    def test_summary_entry_added(self):
        state = {
            "classification": {"category": "withdrawal_issue"},
            "risk_assessment": {"risk_level": "high", "requires_human_review": True},
            "draft_response": {"approval_required": True, "tone": "empathetic"},
            "groundedness_check": {"is_grounded": True},
            "draft_retries": 0,
            "audit_trail": [{"step": "approval_gate"}],
        }
        result = audit_log_node(state)
        trail = result["audit_trail"]
        assert len(trail) == 2
        summary = trail[1]
        assert summary["step"] == "audit_log"
        assert summary["category"] == "withdrawal_issue"
        assert summary["risk_level"] == "high"
        assert summary["requires_human_review"] is True
        assert summary["groundedness"] is True
