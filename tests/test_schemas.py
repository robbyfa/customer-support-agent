"""Tests for Pydantic schema models.

Covers instantiation, Literal validation, optional fields, and serialization.
No LLM calls - these are pure unit tests.
"""

import pytest
from pydantic import ValidationError

from models.classification import TicketClassification


# ---------------------------------------------------------------------------
# TicketClassification
# ---------------------------------------------------------------------------


class TestTicketClassificationInstantiation:
    def test_valid_minimal(self):
        tc = TicketClassification(
            category="withdrawal_issue",
            urgency="high",
            sentiment="negative",
            summary="Customer reports failed withdrawal.",
            requires_human_review=True,
            sensitive_case=False,
        )
        assert tc.category == "withdrawal_issue"
        assert tc.extracted_customer_id is None

    def test_valid_with_customer_id(self):
        tc = TicketClassification(
            category="login_issue",
            urgency="medium",
            sentiment="neutral",
            summary="Customer cannot log in.",
            requires_human_review=False,
            sensitive_case=False,
            extracted_customer_id="CUST-1003",
        )
        assert tc.extracted_customer_id == "CUST-1003"

    def test_all_categories(self):
        for cat in [
            "withdrawal_issue",
            "deposit_issue",
            "login_issue",
            "bonus_issue",
            "account_verification",
            "responsible_gaming",
            "other",
        ]:
            tc = TicketClassification(
                category=cat,
                urgency="low",
                sentiment="neutral",
                summary="Test.",
                requires_human_review=False,
                sensitive_case=False,
            )
            assert tc.category == cat


class TestTicketClassificationValidation:
    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            TicketClassification(
                category="invalid_category",
                urgency="high",
                sentiment="negative",
                summary="Test.",
                requires_human_review=False,
                sensitive_case=False,
            )

    def test_invalid_urgency_raises(self):
        with pytest.raises(ValidationError):
            TicketClassification(
                category="other",
                urgency="critical",
                sentiment="neutral",
                summary="Test.",
                requires_human_review=False,
                sensitive_case=False,
            )

    def test_invalid_sentiment_raises(self):
        with pytest.raises(ValidationError):
            TicketClassification(
                category="other",
                urgency="low",
                sentiment="angry",
                summary="Test.",
                requires_human_review=False,
                sensitive_case=False,
            )

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            TicketClassification(
                category="other",
                urgency="low",
                # sentiment missing
                summary="Test.",
                requires_human_review=False,
                sensitive_case=False,
            )


class TestTicketClassificationSerialization:
    def test_model_dump(self):
        tc = TicketClassification(
            category="responsible_gaming",
            urgency="high",
            sentiment="negative",
            summary="Self-exclusion request.",
            requires_human_review=True,
            sensitive_case=True,
            extracted_customer_id="CUST-1006",
        )
        data = tc.model_dump()
        assert isinstance(data, dict)
        assert data["category"] == "responsible_gaming"
        assert data["extracted_customer_id"] == "CUST-1006"

    def test_model_dump_json(self):
        tc = TicketClassification(
            category="deposit_issue",
            urgency="medium",
            sentiment="neutral",
            summary="Missing deposit.",
            requires_human_review=False,
            sensitive_case=False,
        )
        json_str = tc.model_dump_json()
        assert '"category":"deposit_issue"' in json_str or '"category": "deposit_issue"' in json_str

    def test_round_trip(self):
        tc = TicketClassification(
            category="bonus_issue",
            urgency="low",
            sentiment="positive",
            summary="Bonus question.",
            requires_human_review=False,
            sensitive_case=False,
            extracted_customer_id="CUST-1004",
        )
        data = tc.model_dump()
        tc2 = TicketClassification(**data)
        assert tc == tc2


# ===========================================================================
# SupportRecommendation (Task 9)
# ===========================================================================

from models.recommendation import SupportRecommendation


class TestSupportRecommendationInstantiation:
    def test_valid_full(self):
        r = SupportRecommendation(
            recommended_action="Escalate to Payments Operations",
            reason="3 failed withdrawals per policy",
            relevant_policy_sources=["withdrawal_policy.md"],
            missing_information=["Payment provider error details"],
            human_review_required=True,
        )
        assert r.recommended_action == "Escalate to Payments Operations"
        assert len(r.relevant_policy_sources) == 1

    def test_defaults_for_lists(self):
        r = SupportRecommendation(
            recommended_action="Standard response",
            reason="Low-risk inquiry",
            human_review_required=False,
        )
        assert r.relevant_policy_sources == []
        assert r.missing_information == []


class TestSupportRecommendationValidation:
    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            SupportRecommendation(
                recommended_action="Do something",
                # reason missing
                human_review_required=False,
            )


class TestSupportRecommendationSerialization:
    def test_round_trip(self):
        r = SupportRecommendation(
            recommended_action="Escalate",
            reason="High risk",
            relevant_policy_sources=["escalation_policy.md"],
            missing_information=[],
            human_review_required=True,
        )
        data = r.model_dump()
        r2 = SupportRecommendation(**data)
        assert r == r2


# ===========================================================================
# DraftResponse (Task 9)
# ===========================================================================

from models.response import DraftResponse


class TestDraftResponseInstantiation:
    def test_valid_full(self):
        d = DraftResponse(
            customer_message="We are looking into your issue.",
            tone="empathetic",
            should_send=False,
            approval_required=True,
            reason_approval_required="High-risk case",
        )
        assert d.tone == "empathetic"
        assert d.approval_required is True

    def test_optional_reason(self):
        d = DraftResponse(
            customer_message="Your deposit has been credited.",
            tone="neutral",
            should_send=True,
            approval_required=False,
        )
        assert d.reason_approval_required is None


class TestDraftResponseValidation:
    def test_invalid_tone_raises(self):
        with pytest.raises(ValidationError):
            DraftResponse(
                customer_message="Hello",
                tone="casual",
                should_send=True,
                approval_required=False,
            )

    def test_all_tones(self):
        for tone in ["neutral", "empathetic", "formal"]:
            d = DraftResponse(
                customer_message="Test",
                tone=tone,
                should_send=True,
                approval_required=False,
            )
            assert d.tone == tone


class TestDraftResponseFormatText:
    def test_format_includes_tone(self):
        d = DraftResponse(
            customer_message="We are investigating.",
            tone="empathetic",
            should_send=False,
            approval_required=True,
            reason_approval_required="Sensitive case",
        )
        text = d.format_text()
        assert "Tone: empathetic" in text
        assert "Approval required: Yes" in text
        assert "Reason: Sensitive case" in text
        assert "We are investigating." in text

    def test_format_without_reason(self):
        d = DraftResponse(
            customer_message="All good.",
            tone="neutral",
            should_send=True,
            approval_required=False,
        )
        text = d.format_text()
        assert "Approval required: No" in text
        assert "Reason:" not in text
        assert "All good." in text


class TestDraftResponseSerialization:
    def test_round_trip(self):
        d = DraftResponse(
            customer_message="Test message",
            tone="formal",
            should_send=False,
            approval_required=True,
            reason_approval_required="Compliance hold",
        )
        data = d.model_dump()
        d2 = DraftResponse(**data)
        assert d == d2
