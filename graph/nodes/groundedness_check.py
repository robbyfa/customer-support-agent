"""Node: groundedness_check - verifies both the draft response AND the
recommendation are grounded in policy context before approval.

Dual check:
1. Is the customer-facing message supported by policy?
2. Does the recommendation avoid claiming unconfirmed actions?
"""

from datetime import datetime, timezone
from typing import Any

from graph.chains.groundedness_checker import get_groundedness_chain
from graph.state import GraphState

MAX_RETRIES = 2


def groundedness_check(state: GraphState) -> dict[str, Any]:
    """Check whether both the draft and recommendation are grounded.

    Runs two checks:
    1. Draft groundedness - is the customer message policy-supported?
    2. Recommendation validity - does it avoid claiming completed actions?

    Both must pass for the overall check to be grounded.
    """
    draft = state.get("draft_response", {})
    recommendation = state.get("recommendation", {})
    policy_context = state.get("policy_context", [])
    policy_text = "\n\n".join(policy_context) if policy_context else "No policy context."

    chain = get_groundedness_chain()

    # 1. Check customer-facing draft
    draft_result = chain.invoke(
        {
            "draft_response": draft.get("customer_message", ""),
            "policy_context": policy_text,
        }
    )
    draft_check = draft_result.model_dump()

    # 2. Check internal recommendation
    rec_text = (
        f"Action: {recommendation.get('recommended_action', '')}\n"
        f"Reason: {recommendation.get('reason', '')}"
    )
    rec_result = chain.invoke(
        {
            "draft_response": rec_text,
            "policy_context": policy_text,
        }
    )
    rec_check = rec_result.model_dump()

    # Combined result - both must be grounded
    all_issues = draft_check.get("issues", []) + rec_check.get("issues", [])
    is_grounded = draft_check["is_grounded"] and rec_check["is_grounded"]
    confidence = min(draft_check["confidence"], rec_check["confidence"])

    check = {
        "is_grounded": is_grounded,
        "confidence": confidence,
        "issues": all_issues,
        "draft_grounded": draft_check["is_grounded"],
        "recommendation_grounded": rec_check["is_grounded"],
    }

    retries = state.get("draft_retries", 0)

    audit_entry = {
        "step": "groundedness_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_grounded": is_grounded,
        "draft_grounded": draft_check["is_grounded"],
        "recommendation_grounded": rec_check["is_grounded"],
        "confidence": confidence,
        "issues_count": len(all_issues),
        "retry_number": retries,
    }

    return {
        "groundedness_check": check,
        "draft_retries": retries + (0 if is_grounded else 1),
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
