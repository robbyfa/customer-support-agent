"""MCP server exposing customer support tools and policy resources.

This server provides a standard MCP interface over the same mock data
that the LangGraph agent uses directly. It demonstrates:

- **Tools**: get_customer_profile, get_ticket_history,
             get_recent_transactions, get_bonus_status
- **Resources**: policy documents accessible by URI

Run standalone:
    uv run python mcp_server/server.py              # stdio
    uv run python mcp_server/server.py --transport http --port 8100  # HTTP
"""

import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Ensure project root is on sys.path so storage imports work
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from storage.mock_data import (
    get_customer,
    get_customer_bonus,
    get_customer_tickets,
    get_customer_transactions,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="Customer Support MCP Server",
)

# ---------------------------------------------------------------------------
# Tools - executable functions for the agent
# ---------------------------------------------------------------------------


@mcp.tool()
def get_customer_profile(customer_id: str) -> dict[str, Any]:
    """Look up a customer profile by their ID (e.g. CUST-1001).

    Returns the full customer record including account status,
    verification status, risk level, and responsible gaming flags.
    """
    customer = get_customer(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}
    return customer


@mcp.tool()
def get_ticket_history(customer_id: str) -> dict[str, Any]:
    """Retrieve the support ticket history for a customer.

    Returns all past and open tickets including category, status,
    and priority. Useful for understanding recurring issues.
    """
    customer = get_customer(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}
    tickets = get_customer_tickets(customer_id)
    return {
        "customer_id": customer_id,
        "total_tickets": len(tickets),
        "tickets": tickets,
    }


@mcp.tool()
def get_recent_transactions(customer_id: str) -> dict[str, Any]:
    """Retrieve the transaction history for a customer.

    Returns deposits, withdrawals, and failed attempts.
    Useful for investigating payment issues.
    """
    customer = get_customer(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}
    transactions = get_customer_transactions(customer_id)
    return {
        "customer_id": customer_id,
        "total_transactions": len(transactions),
        "transactions": transactions,
    }


@mcp.tool()
def get_bonus_status(customer_id: str) -> dict[str, Any]:
    """Check the bonus history and active bonus status for a customer.

    Returns all bonus records including wagering progress.
    """
    customer = get_customer(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}
    bonuses = get_customer_bonus(customer_id)
    active = [b for b in bonuses if b["status"] == "active"]
    return {
        "customer_id": customer_id,
        "has_active_bonus": len(active) > 0,
        "active_bonuses": active,
        "bonus_history": bonuses,
    }


# ---------------------------------------------------------------------------
# Resources - policy documents accessible by URI
# ---------------------------------------------------------------------------

_POLICIES_DIR = _PROJECT_ROOT / "data" / "policies"


@mcp.resource("policy://list")
def list_policies() -> str:
    """List all available policy documents."""
    policies = sorted(p.name for p in _POLICIES_DIR.glob("*.md"))
    return json.dumps({"policies": policies, "total": len(policies)})


@mcp.resource("policy://{policy_name}")
def get_policy(policy_name: str) -> str:
    """Retrieve a specific policy document by filename.

    Example URIs:
        policy://withdrawal_policy.md
        policy://responsible_gaming_policy.md
    """
    policy_path = _POLICIES_DIR / policy_name
    if not policy_path.exists() or policy_path.suffix != ".md":
        return json.dumps({"error": f"Policy '{policy_name}' not found"})
    return policy_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Run standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Customer Support MCP Server")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    parser.add_argument("--port", type=int, default=8100)
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="streamable-http", port=args.port)
    else:
        mcp.run(transport="stdio")
