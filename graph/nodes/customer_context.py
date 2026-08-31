"""Node: customer_context - aggregates customer profile, transactions,
tickets, and bonus data into a single context dict.
"""

from datetime import datetime, timezone
from typing import Any

from graph.state import GraphState
from storage.mock_data import (
    get_customer,
    get_customer_bonus,
    get_customer_tickets,
    get_customer_transactions,
)


def get_customer_context(state: GraphState) -> dict[str, Any]:
    """Build a comprehensive customer context from mock data.

    Reads ``customer_id`` from state and returns:
    - customer_context: dict with profile, transactions, tickets, bonus, flags
    - audit_trail: appended entry for this step
    """
    customer_id = state.get("customer_id")

    if not customer_id:
        return {
            "customer_context": {"error": "No customer_id provided"},
            "audit_trail": state.get("audit_trail", []) + [
                {
                    "step": "customer_context",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
                    "step": "customer_context",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": f"Customer {customer_id} not found",
                }
            ],
        }

    transactions = get_customer_transactions(customer_id)
    tickets = get_customer_tickets(customer_id)
    bonuses = get_customer_bonus(customer_id)

    failed_withdrawals = [
        t for t in transactions
        if t["type"] == "withdrawal" and t["status"] == "failed"
    ]

    flags = {
        "has_failed_withdrawals": len(failed_withdrawals) > 0,
        "failed_withdrawal_count": len(failed_withdrawals),
        "account_locked": profile.get("account_status") == "locked",
        "verification_pending": profile.get("verification_status") == "pending",
        "responsible_gaming_flag": profile.get("responsible_gaming_flag", False),
        "has_active_bonus": profile.get("active_bonus", False),
        "risk_level": profile.get("risk_level", "low"),
    }

    context = {
        "profile": profile,
        "transactions": transactions,
        "tickets": tickets,
        "bonuses": bonuses,
        "flags": flags,
    }

    audit_entry = {
        "step": "customer_context",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": customer_id,
        "transactions_found": len(transactions),
        "tickets_found": len(tickets),
        "bonuses_found": len(bonuses),
    }

    return {
        "customer_context": context,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
