"""Node: groundedness_check - verifies that the draft response is
grounded in the provided policy context before approval.
"""

from datetime import datetime, timezone
from typing import Any

from graph.chains.groundedness_checker import get_groundedness_chain
from graph.state import GraphState

MAX_RETRIES = 2


def groundedness_check(state: GraphState) -> dict[str, Any]:
    """Check whether the draft response is grounded in policy.

    Invokes the groundedness chain and stores the result.
    The routing function after this node decides whether to retry
    or proceed to the approval gate.
    """
    draft = state.get("draft_response", {})
    policy_context = state.get("policy_context", [])

    chain = get_groundedness_chain()
    result = chain.invoke(
        {
            "draft_response": draft.get("customer_message", ""),
            "policy_context": "\n\n".join(policy_context) if policy_context else "No policy context.",
        }
    )

    check = result.model_dump()
    retries = state.get("draft_retries", 0)

    audit_entry = {
        "step": "groundedness_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_grounded": check["is_grounded"],
        "confidence": check["confidence"],
        "issues_count": len(check.get("issues", [])),
        "retry_number": retries,
    }

    return {
        "groundedness_check": check,
        "draft_retries": retries + (0 if check["is_grounded"] else 1),
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
