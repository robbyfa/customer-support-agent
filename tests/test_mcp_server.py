"""Tests for the MCP server - tools and resources.

These tests spin up the MCP server via stdio and call tools/resources
through the MCP client. No LLM needed.
"""

import asyncio
import json

from mcp_server.client import (
    call_mcp_tool,
    get_mcp_session,
    list_mcp_resources,
    read_mcp_resource,
)


def _run(coro):
    """Helper to run async in sync tests."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


class TestMCPToolGetCustomerProfile:
    def test_known_customer(self):
        result = _run(call_mcp_tool("get_customer_profile", {"customer_id": "CUST-1001"}))
        assert result["customer_id"] == "CUST-1001"
        assert result["name"] == "Maria Gonzalez"

    def test_unknown_customer(self):
        result = _run(call_mcp_tool("get_customer_profile", {"customer_id": "CUST-9999"}))
        assert "error" in result


class TestMCPToolGetTicketHistory:
    def test_known_customer(self):
        result = _run(call_mcp_tool("get_ticket_history", {"customer_id": "CUST-1001"}))
        assert result["total_tickets"] == 3

    def test_unknown_customer(self):
        result = _run(call_mcp_tool("get_ticket_history", {"customer_id": "CUST-9999"}))
        assert "error" in result


class TestMCPToolGetRecentTransactions:
    def test_known_customer(self):
        result = _run(call_mcp_tool("get_recent_transactions", {"customer_id": "CUST-1001"}))
        assert result["total_transactions"] == 5

    def test_failed_withdrawals(self):
        result = _run(call_mcp_tool("get_recent_transactions", {"customer_id": "CUST-1001"}))
        failed = [t for t in result["transactions"] if t["type"] == "withdrawal" and t["status"] == "failed"]
        assert len(failed) == 3


class TestMCPToolGetBonusStatus:
    def test_customer_with_active_bonus(self):
        result = _run(call_mcp_tool("get_bonus_status", {"customer_id": "CUST-1004"}))
        assert result["has_active_bonus"] is True

    def test_customer_without_bonus(self):
        result = _run(call_mcp_tool("get_bonus_status", {"customer_id": "CUST-1005"}))
        assert result["has_active_bonus"] is False


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------


class TestMCPResources:
    def test_list_resources(self):
        async def _test():
            async with get_mcp_session() as session:
                resources = await list_mcp_resources(session)
                assert len(resources) >= 1
                uris = [r["uri"] for r in resources]
                assert "policy://list" in uris

        _run(_test())

    def test_read_policy_list(self):
        async def _test():
            async with get_mcp_session() as session:
                content = await read_mcp_resource(session, "policy://list")
                data = json.loads(content)
                assert data["total"] == 7
                assert "withdrawal_policy.md" in data["policies"]

        _run(_test())

    def test_read_specific_policy(self):
        async def _test():
            async with get_mcp_session() as session:
                content = await read_mcp_resource(
                    session, "policy://withdrawal_policy.md"
                )
                assert "Withdrawal Policy" in content
                assert "failed withdrawals" in content.lower()

        _run(_test())


# ---------------------------------------------------------------------------
# MCP-backed graph nodes
# ---------------------------------------------------------------------------


class TestMCPBackedNodes:
    def test_customer_context_via_mcp(self):
        from graph.nodes.customer_context import get_customer_context

        state = {"customer_id": "CUST-1001", "audit_trail": []}
        result = get_customer_context(state)
        ctx = result["customer_context"]

        assert ctx["flags"]["failed_withdrawal_count"] == 3
        assert len(ctx["transactions"]) == 5
        assert len(ctx["tickets"]) == 3

        # Verify audit trail records MCP as source
        trail = result["audit_trail"]
        assert trail[-1]["source"] == "mcp"

    def test_minimal_context_via_mcp(self):
        from graph.nodes.minimal_customer_context import get_minimal_customer_context

        state = {"customer_id": "CUST-1006", "audit_trail": []}
        result = get_minimal_customer_context(state)
        ctx = result["customer_context"]

        assert ctx["flags"]["responsible_gaming_flag"] is True
        assert ctx["transactions"] == []
        assert trail[-1]["source"] == "mcp" if (trail := result["audit_trail"]) else False

    def test_unknown_customer_via_mcp(self):
        from graph.nodes.customer_context import get_customer_context

        state = {"customer_id": "CUST-9999", "audit_trail": []}
        result = get_customer_context(state)
        assert "error" in result["customer_context"]
