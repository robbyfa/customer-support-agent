"""Tests for Pydantic schema models.

Covers instantiation, Literal validation, optional fields, and serialization.
No LLM calls — these are pure unit tests.
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
