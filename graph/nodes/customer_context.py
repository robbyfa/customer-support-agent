"""Node: customer_context - aggregates customer profile, transactions,
tickets, and bonus data via the MCP server.

Uses the MCP client to call tools on the Customer Support MCP Server
instead of importing storage functions directly.
"""

from datetime import UTC, datetime
from typing import Any

from graph.state import GraphState
from mcp_server.client import call_mcp_tool_sync


def get_customer_context(state: GraphState) -> dict[str, Any]:
    """Build a comprehensive customer context via MCP tool calls.

    Calls the MCP server's tools for profile, transactions, tickets,
    and bonuses, then assembles flags for downstream nodes.
    """
    customer_id = state.get("customer_id")

    if not customer_id:
        return {
            "customer_context": {"error": "No customer_id provided"},
            "audit_trail": state.get("audit_trail", []) + [
                {
                    "step": "customer_context",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": "No customer_id provided",
                    "source": "mcp",
                }
            ],
        }

    # Call MCP tools
    profile = call_mcp_tool_sync("get_customer_profile", {"customer_id": customer_id})

    if isinstance(profile, dict) and "error" in profile:
        return {
            "customer_context": {"error": profile["error"]},
            "audit_trail": state.get("audit_trail", []) + [
                {
                    "step": "customer_context",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "error": profile["error"],
                    "source": "mcp",
                }
            ],
        }

    txn_result = call_mcp_tool_sync("get_recent_transactions", {"customer_id": customer_id})
    ticket_result = call_mcp_tool_sync("get_ticket_history", {"customer_id": customer_id})
    bonus_result = call_mcp_tool_sync("get_bonus_status", {"customer_id": customer_id})

    transactions = txn_result.get("transactions", []) if isinstance(txn_result, dict) else []
    tickets = ticket_result.get("tickets", []) if isinstance(ticket_result, dict) else []
    bonuses = bonus_result.get("bonus_history", []) if isinstance(bonus_result, dict) else []

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
        "timestamp": datetime.now(UTC).isoformat(),
        "customer_id": customer_id,
        "source": "mcp",
        "transactions_found": len(transactions),
        "tickets_found": len(tickets),
        "bonuses_found": len(bonuses),
    }

    return {
        "customer_context": context,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
