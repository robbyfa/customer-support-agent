"""Node: manual_review_response - fallback when the draft response fails
groundedness checks after all retries.

Replaces the ungrounded draft AND the stale recommendation with safe
content flagged for manual review.
"""

from datetime import datetime, timezone
from typing import Any

from graph.state import GraphState


_MANUAL_REVIEW_TEMPLATE = (
    "Thank you for contacting us. Your case will be reviewed by a "
    "specialist. A member of our team will follow up with you shortly. "
    "We appreciate your patience."
)


def manual_review_response(state: GraphState) -> dict[str, Any]:
    """Replace the ungrounded draft and stale recommendation.

    Sets approval_required=True so the case always goes through the
    approval gate as pending review.
    """
    classification = state.get("classification", {})
    risk = state.get("risk_assessment", {})
    gc = state.get("groundedness_check", {})

    draft = {
        "customer_message": _MANUAL_REVIEW_TEMPLATE,
        "tone": "formal",
        "should_send": False,
        "approval_required": True,
        "reason_approval_required": (
            "Draft failed groundedness check after maximum retries. "
            "Replaced with safe template for manual review."
        ),
    }

    # Replace the stale recommendation with a rejected status
    recommendation = {
        "recommended_action": "Manual review required - original draft was not grounded in policy.",
        "reason": (
            f"Groundedness check failed: {'; '.join(gc.get('issues', []))}"
            if gc.get("issues")
            else "Draft could not be verified against policy context."
        ),
        "relevant_policy_sources": [],
        "missing_information": [],
        "human_review_required": True,
        "status": "rejected_by_groundedness_check",
    }

    audit_entry = {
        "step": "manual_review_response",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": "Groundedness check failed after max retries",
        "original_category": classification.get("category", "unknown"),
        "risk_level": risk.get("risk_level", "unknown"),
    }

    return {
        "draft_response": draft,
        "recommendation": recommendation,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
