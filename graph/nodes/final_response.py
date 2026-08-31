"""Node: final_response - assembles all state pieces into the final
output presented to the support agent.
"""

from datetime import datetime, timezone
from typing import Any

from graph.state import GraphState


def final_response(state: GraphState) -> dict[str, Any]:
    """Assemble the final copilot output from all accumulated state.

    Returns:
    - final_output: dict with all sections the support agent needs
    - audit_trail: appended entry
    """
    classification = state.get("classification", {})
    risk_assessment = state.get("risk_assessment", {})
    draft = state.get("draft_response", {})
    recommendation = state.get("recommendation", {})
    approved = state.get("approved")

    final_output = {
        "customer_message": state.get("customer_message", ""),
        "customer_id": state.get("customer_id"),
        "classification": classification,
        "policy_context": state.get("policy_context", []),
        "customer_context": state.get("customer_context", {}),
        "risk_assessment": risk_assessment,
        "recommendation": recommendation,
        "draft_response": draft,
        "approved": approved,
        "status": "approved" if approved else "pending_review",
    }

    audit_entry = {
        "step": "final_response",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": final_output["status"],
    }

    return {
        "final_output": final_output,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
