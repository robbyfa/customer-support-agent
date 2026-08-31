"""Node: approval_gate - determines whether the draft response can be
sent automatically or requires human approval.
"""

from datetime import datetime, timezone
from typing import Any

from graph.state import GraphState


def approval_gate(state: GraphState) -> dict[str, Any]:
    """Decide whether the draft response is approved for sending.

    Logic:
    - If risk_assessment says human review is required → not approved.
    - If draft_response says approval_required → not approved.
    - If classification is sensitive_case → not approved.
    - Otherwise → approved.

    Returns:
    - approved: bool
    - audit_trail: appended entry
    """
    risk = state.get("risk_assessment", {})
    draft = state.get("draft_response", {})
    classification = state.get("classification", {})

    requires_review = (
        risk.get("requires_human_review", False)
        or draft.get("approval_required", False)
        or classification.get("sensitive_case", False)
    )

    approved = not requires_review

    audit_entry = {
        "step": "approval_gate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "approved": approved,
        "reason": "Auto-approved - no review flags" if approved else "Held for human review",
    }

    return {
        "approved": approved,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
