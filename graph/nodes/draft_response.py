"""Node: draft_response - generates both:
1. A customer-facing draft response (what to SAY)
2. An internal action recommendation (what to DO)

These are produced by separate LLM chains with different prompts.
"""

import json
from datetime import datetime, timezone
from typing import Any

from graph.chains.recommendation_generator import get_recommendation_chain
from graph.chains.response_generator import get_response_chain
from graph.state import GraphState


def draft_response(state: GraphState) -> dict[str, Any]:
    """Generate a draft response and a separate internal recommendation.

    Returns:
    - draft_response: dict - the customer-facing message (DraftResponse)
    - recommendation: dict - the internal agent action (SupportRecommendation)
    - audit_trail: appended entry
    """
    classification = state.get("classification", {})
    risk_assessment = state.get("risk_assessment", {})
    policy_context = state.get("policy_context", [])
    customer_context = state.get("customer_context", {})

    policy_text = "\n\n".join(policy_context) if policy_context else "No policy context available."
    classification_json = json.dumps(classification)
    context_json = json.dumps(customer_context, default=str)
    risk_json = json.dumps(risk_assessment)

    # 1. Generate customer-facing draft
    response_chain = get_response_chain()
    draft_result = response_chain.invoke(
        {
            "customer_message": state.get("customer_message", ""),
            "classification": classification_json,
            "policy_context": policy_text,
            "customer_context": context_json,
            "risk_assessment": risk_json,
        }
    )
    draft = draft_result.model_dump()

    # 2. Generate internal recommendation (separate LLM call)
    rec_chain = get_recommendation_chain()
    rec_result = rec_chain.invoke(
        {
            "classification": classification_json,
            "policy_context": policy_text,
            "customer_context": context_json,
            "risk_assessment": risk_json,
        }
    )
    recommendation = rec_result.model_dump()

    audit_entry = {
        "step": "draft_response",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tone": draft["tone"],
        "approval_required": draft["approval_required"],
        "recommended_action": recommendation["recommended_action"][:100],
    }

    return {
        "draft_response": draft,
        "recommendation": recommendation,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
