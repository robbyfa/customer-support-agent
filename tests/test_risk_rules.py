"""Tests for rule-based risk assessment (graph/nodes/risk_check.py).

Pure unit tests - no LLM calls needed.
"""

from graph.nodes.risk_check import risk_check


def _make_state(
    category="other",
    urgency="low",
    sentiment="neutral",
    sensitive_case=False,
    requires_human_review=False,
    failed_withdrawal_count=0,
    responsible_gaming_flag=False,
    account_locked=False,
):
    """Helper to build a minimal state dict for risk_check."""
    return {
        "classification": {
            "category": category,
            "urgency": urgency,
            "sentiment": sentiment,
            "sensitive_case": sensitive_case,
            "requires_human_review": requires_human_review,
        },
        "customer_context": {
            "flags": {
                "failed_withdrawal_count": failed_withdrawal_count,
                "has_failed_withdrawals": failed_withdrawal_count > 0,
                "responsible_gaming_flag": responsible_gaming_flag,
                "account_locked": account_locked,
            },
        },
        "audit_trail": [],
    }


# ---------------------------------------------------------------------------
# Rule 1: Responsible gaming → always high + human review
# ---------------------------------------------------------------------------


class TestResponsibleGaming:
    def test_responsible_gaming_category_is_high_risk(self):
        state = _make_state(category="responsible_gaming")
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] == "high"
        assert ra["requires_human_review"] is True

    def test_responsible_gaming_flag_on_profile(self):
        state = _make_state(
            category="withdrawal_issue", responsible_gaming_flag=True
        )
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] == "high"
        assert ra["requires_human_review"] is True


# ---------------------------------------------------------------------------
# Rule 3: Withdrawal + 3 failures + negative → high + human review
# ---------------------------------------------------------------------------


class TestWithdrawalFailures:
    def test_three_failures_negative_sentiment(self):
        state = _make_state(
            category="withdrawal_issue",
            urgency="high",
            sentiment="negative",
            failed_withdrawal_count=3,
        )
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] == "high"
        assert ra["requires_human_review"] is True
        # Should mention the failure count
        factors = " ".join(ra["risk_factors"]).lower()
        assert "3 failed withdrawals" in factors

    def test_three_failures_neutral_sentiment(self):
        state = _make_state(
            category="withdrawal_issue",
            urgency="medium",
            sentiment="neutral",
            failed_withdrawal_count=3,
        )
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] == "high"
        assert ra["requires_human_review"] is True


# ---------------------------------------------------------------------------
# Rule 4: Negative sentiment + high urgency → elevated
# ---------------------------------------------------------------------------


class TestNegativeHighUrgency:
    def test_negative_high_urgency_elevates_risk(self):
        state = _make_state(
            category="deposit_issue", urgency="high", sentiment="negative"
        )
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] == "high"


# ---------------------------------------------------------------------------
# Rule 5: sensitive_case flag → human review
# ---------------------------------------------------------------------------


class TestSensitiveCase:
    def test_sensitive_case_requires_human_review(self):
        state = _make_state(sensitive_case=True)
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["requires_human_review"] is True

    def test_sensitive_case_at_least_medium(self):
        state = _make_state(sensitive_case=True, urgency="low", sentiment="neutral")
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] in ("medium", "high")


# ---------------------------------------------------------------------------
# Low-risk standard cases
# ---------------------------------------------------------------------------


class TestLowRiskCases:
    def test_login_neutral_is_low_or_medium(self):
        state = _make_state(category="login_issue", urgency="medium", sentiment="neutral")
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] in ("low", "medium")
        assert ra["requires_human_review"] is False

    def test_bonus_low_positive_is_low(self):
        state = _make_state(category="bonus_issue", urgency="low", sentiment="positive")
        result = risk_check(state)
        ra = result["risk_assessment"]
        assert ra["risk_level"] == "low"
        assert ra["requires_human_review"] is False


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------


class TestRiskCheckAudit:
    def test_audit_trail_appended(self):
        state = _make_state()
        state["audit_trail"] = [{"step": "previous"}]
        result = risk_check(state)
        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "risk_check"
        assert "risk_level" in trail[1]
        assert "requires_human_review" in trail[1]
