"""Node: minimal_customer_context - lightweight customer context for
sensitive cases (responsible gaming, etc.).

Only fetches the profile and risk flags - no transactions, tickets, or
bonuses - to fast-track sensitive cases while still having enough context
for risk assessment and response generation.
"""

from datetime import UTC, datetime
from typing import Any

from graph.state import GraphState
from storage.mock_data import get_customer


def get_minimal_customer_context(state: GraphState) -> dict[str, Any]:
    """Build a minimal customer context with profile and flags only.

    Used for sensitive cases where the priority is speed and safety,
    not deep transaction analysis.
    """
    customer_id = state.get("customer_id")

    if not customer_id:
        return {
            "customer_context": {"error": "No customer_id provided"},
            "audit_trail": state.get("audit_trail", []) + [
                {
                    "step": "minimal_customer_context",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": "No customer_id provided",
                }
            ],
        }

    profile = get_customer(customer_id)

    if profile is None:
        return {
            "customer_context": {"error": f"Customer {customer_id} not found"},
            "audit_trail": state.get("audit_trail", []) + [
                {
                    "step": "minimal_customer_context",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": f"Customer {customer_id} not found",
                }
            ],
        }

    flags = {
        "has_failed_withdrawals": False,
        "failed_withdrawal_count": 0,
        "account_locked": profile.get("account_status") == "locked",
        "verification_pending": profile.get("verification_status") == "pending",
        "responsible_gaming_flag": profile.get("responsible_gaming_flag", False),
        "has_active_bonus": profile.get("active_bonus", False),
        "risk_level": profile.get("risk_level", "low"),
    }

    context = {
        "profile": profile,
        "transactions": [],
        "tickets": [],
        "bonuses": [],
        "flags": flags,
    }

    audit_entry = {
        "step": "minimal_customer_context",
        "timestamp": datetime.now(UTC).isoformat(),
        "customer_id": customer_id,
        "mode": "minimal - sensitive case fast-track",
    }

    return {
        "customer_context": context,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
