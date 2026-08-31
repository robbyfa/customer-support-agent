"""Node: draft_response - generates a draft customer-facing response and
an internal support recommendation using the response chain.
"""

import json
from datetime import datetime, timezone
from typing import Any

from graph.chains.response_generator import get_response_chain
from graph.state import GraphState


def draft_response(state: GraphState) -> dict[str, Any]:
    """Generate a draft response and recommendation for the support agent.

    Feeds full context (message, classification, policy, customer, risk)
    into the response chain and returns:
    - draft_response: dict representation of DraftResponse
    - recommendation: dict with action, reason, sources, etc.
    - audit_trail: appended entry
    """
    classification = state.get("classification", {})
    risk_assessment = state.get("risk_assessment", {})
    policy_context = state.get("policy_context", [])
    customer_context = state.get("customer_context", {})

    chain = get_response_chain()
    result = chain.invoke(
        {
            "customer_message": state.get("customer_message", ""),
            "classification": json.dumps(classification),
            "policy_context": "\n\n".join(policy_context) if policy_context else "No policy context available.",
            "customer_context": json.dumps(customer_context, default=str),
            "risk_assessment": json.dumps(risk_assessment),
        }
    )

    draft = result.model_dump()

    # Build recommendation from the combined context
    recommendation = {
        "recommended_action": draft["customer_message"][:200],
        "reason": f"Based on {classification.get('category', 'unknown')} classification and risk level {risk_assessment.get('risk_level', 'unknown')}",
        "relevant_policy_sources": _extract_sources(policy_context),
        "missing_information": [],
        "human_review_required": risk_assessment.get("requires_human_review", False),
    }

    audit_entry = {
        "step": "draft_response",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tone": draft["tone"],
        "approval_required": draft["approval_required"],
    }

    return {
        "draft_response": draft,
        "recommendation": recommendation,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }


def _extract_sources(policy_context: list[str]) -> list[str]:
    """Best-effort extraction of source filenames from policy chunks."""
    # Policy chunks don't carry metadata at this layer, so we return
    # a placeholder indicating policy was used.
    if policy_context:
        return ["policy_documents"]
    return []
