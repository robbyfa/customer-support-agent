"""Node: draft_response - generates a draft customer-facing response and
an internal support recommendation using the response chain.
"""

import json
from datetime import datetime, timezone
from typing import Any

from graph.chains.response_generator import get_response_chain
from graph.state import GraphState
from models.recommendation import SupportRecommendation


def draft_response(state: GraphState) -> dict[str, Any]:
    """Generate a draft response and recommendation for the support agent.

    Feeds full context (message, classification, policy, customer, risk)
    into the response chain and returns:
    - draft_response: dict representation of DraftResponse
    - recommendation: dict representation of SupportRecommendation
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
    missing = _identify_missing_information(classification, customer_context, risk_assessment)

    recommendation = SupportRecommendation(
        recommended_action=draft["customer_message"],
        reason=(
            f"Based on {classification.get('category', 'unknown')} classification "
            f"and risk level {risk_assessment.get('risk_level', 'unknown')}"
        ),
        relevant_policy_sources=_extract_sources(policy_context),
        missing_information=missing,
        human_review_required=risk_assessment.get("requires_human_review", False),
    )

    audit_entry = {
        "step": "draft_response",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tone": draft["tone"],
        "approval_required": draft["approval_required"],
    }

    return {
        "draft_response": draft,
        "recommendation": recommendation.model_dump(),
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }


def _extract_sources(policy_context: list[str]) -> list[str]:
    """Extract source filenames from section-prefixed policy chunks."""
    sources = set()
    for chunk in policy_context:
        for line in chunk.split("\n")[:2]:
            if line.startswith("Source: "):
                sources.add(line.replace("Source: ", "").strip())
    return sorted(sources) if sources else ["policy_documents"]


def _identify_missing_information(
    classification: dict,
    customer_context: dict,
    risk_assessment: dict,
) -> list[str]:
    """Identify what information is still needed to fully resolve the case.

    Uses the category, customer flags, and risk level to determine gaps.
    """
    missing: list[str] = []
    category = classification.get("category", "other")
    flags = customer_context.get("flags", {}) if isinstance(customer_context, dict) else {}

    if category == "withdrawal_issue":
        if flags.get("failed_withdrawal_count", 0) > 0:
            missing.append("payment_provider_error_details")
            missing.append("payment_operations_confirmation")
        missing.append("current_withdrawal_status")

    elif category == "deposit_issue":
        missing.append("payment_provider_transaction_status")
        missing.append("bank_confirmation_or_screenshot")

    elif category == "login_issue":
        if flags.get("account_locked"):
            missing.append("identity_verification_result")
        missing.append("security_team_assessment")

    elif category == "bonus_issue":
        missing.append("wagering_progress_verification")
        missing.append("promotions_team_confirmation")

    elif category == "account_verification":
        missing.append("verification_queue_status")
        missing.append("expected_review_timeline")
        if risk_assessment.get("requires_human_review"):
            missing.append("compliance_team_review_status")

    elif category == "responsible_gaming":
        missing.append("responsible_gaming_team_confirmation")
        missing.append("self_exclusion_period_confirmation")

    return missing
