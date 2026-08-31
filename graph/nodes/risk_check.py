"""Node: risk_check - rule-based risk assessment combining classification,
customer context, and policy signals to determine risk level and whether
human review is required.
"""

from datetime import datetime, timezone
from typing import Any

from graph.state import GraphState


def risk_check(state: GraphState) -> dict[str, Any]:
    """Evaluate the risk level of the current support case.

    Rules (evaluated in priority order):
    1. Responsible gaming → always high risk + human review.
    2. sensitive_case flag → human review required.
    3. Withdrawal + 3+ failures + negative sentiment → high risk + human review.
    4. Negative sentiment + high urgency → elevated to high risk.
    5. Everything else scored on base category/urgency.

    Returns:
    - risk_assessment: dict with risk_level, requires_human_review, risk_factors
    - audit_trail: appended entry
    """
    classification = state.get("classification", {})
    customer_context = state.get("customer_context", {})
    flags = customer_context.get("flags", {}) if isinstance(customer_context, dict) else {}

    category = classification.get("category", "other")
    urgency = classification.get("urgency", "low")
    sentiment = classification.get("sentiment", "neutral")
    sensitive_case = classification.get("sensitive_case", False)
    requires_human = classification.get("requires_human_review", False)

    risk_level = "low"
    risk_factors: list[str] = []

    # --- Rule 1: Responsible gaming is always high risk ---
    if category == "responsible_gaming":
        risk_level = "high"
        requires_human = True
        risk_factors.append("Responsible gaming case - mandatory human review")

    # --- Rule 2: Responsible gaming flag on customer profile ---
    if flags.get("responsible_gaming_flag"):
        risk_level = "high"
        requires_human = True
        risk_factors.append("Customer has active responsible gaming flag")

    # --- Rule 3: Withdrawal failures pattern ---
    failed_count = flags.get("failed_withdrawal_count", 0)
    if category == "withdrawal_issue" and failed_count >= 3:
        risk_level = "high"
        requires_human = True
        risk_factors.append(f"Customer has {failed_count} failed withdrawals")

    if category == "withdrawal_issue" and failed_count >= 3 and sentiment == "negative":
        risk_factors.append("Negative sentiment with repeated withdrawal failures")

    # --- Rule 4: Negative sentiment + high urgency ---
    if sentiment == "negative" and urgency == "high" and risk_level != "high":
        risk_level = "high"
        risk_factors.append("Negative sentiment combined with high urgency")

    # --- Rule 5: sensitive_case flag ---
    if sensitive_case:
        requires_human = True
        if risk_level != "high":
            risk_level = "medium"
        risk_factors.append("Classified as sensitive case")

    # --- Base scoring if still low ---
    if risk_level == "low":
        if urgency == "high":
            risk_level = "medium"
            risk_factors.append("High urgency issue")
        elif urgency == "medium" and sentiment == "negative":
            risk_level = "medium"
            risk_factors.append("Medium urgency with negative sentiment")

    if not risk_factors:
        risk_factors.append("Standard case - no elevated risk factors detected")

    risk_assessment = {
        "risk_level": risk_level,
        "requires_human_review": requires_human,
        "risk_factors": risk_factors,
        "category": category,
        "urgency": urgency,
        "sentiment": sentiment,
    }

    audit_entry = {
        "step": "risk_check",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_level": risk_level,
        "requires_human_review": requires_human,
        "risk_factors_count": len(risk_factors),
    }

    return {
        "risk_assessment": risk_assessment,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
