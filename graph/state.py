"""Graph state definition for the Customer Support Resolution Agent."""

from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    """State passed through every node in the support copilot graph.

    Fields:
        customer_message: The raw message from the customer.
        customer_id: Extracted or provided customer identifier (e.g. CUST-1001).
        classification: TicketClassification dict - category, urgency, sentiment, etc.
        policy_context: Retrieved policy documents relevant to the classified issue.
        customer_context: Aggregated customer profile, transactions, tickets, bonuses.
        risk_assessment: Risk analysis result including risk level and review flags.
        recommendation: SupportRecommendation dict - suggested action, reasons, sources.
        draft_response: DraftResponse dict - proposed customer-facing message.
        groundedness_check: Result of policy groundedness verification.
        draft_retries: Number of times the draft has been regenerated for groundedness.
        approved: Whether the human approval gate approved the draft.
        final_output: Assembled final output with all sections for the support agent.
        audit_trail: List of dicts tracking each node's execution metadata.
    """

    customer_message: str
    customer_id: str | None
    classification: dict[str, Any] | None
    policy_context: list[str]
    customer_context: dict[str, Any] | None
    risk_assessment: dict[str, Any] | None
    recommendation: dict[str, Any] | None
    draft_response: dict[str, Any] | None
    groundedness_check: dict[str, Any] | None
    draft_retries: int
    approved: bool | None
    final_output: dict[str, Any] | None
    audit_trail: list[dict[str, Any]]
