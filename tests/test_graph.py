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
