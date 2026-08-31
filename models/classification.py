"""Pydantic model for structured ticket classification output."""

from typing import Literal

from pydantic import BaseModel, Field


class TicketClassification(BaseModel):
    """Structured classification of a customer support message.

    Produced by the classification chain and consumed by downstream
    nodes for routing, risk assessment, and response generation.
    """

    category: Literal[
        "withdrawal_issue",
        "deposit_issue",
        "login_issue",
        "bonus_issue",
        "account_verification",
        "responsible_gaming",
        "other",
    ] = Field(description="The primary issue category.")

    urgency: Literal["low", "medium", "high"] = Field(
        description="How urgently the issue needs attention."
    )

    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="The customer's emotional tone."
    )

    summary: str = Field(
        description="A brief one-sentence summary of the customer's issue."
    )

    requires_human_review: bool = Field(
        description="Whether this ticket should be flagged for human review."
    )

    sensitive_case: bool = Field(
        description=(
            "Whether this is a sensitive case (responsible gaming, fraud, "
            "account compromise, etc.)."
        )
    )

    extracted_customer_id: str | None = Field(
        default=None,
        description="Customer ID extracted from the message, if present.",
    )
