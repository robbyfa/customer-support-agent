from tools.customer_tools import (
    get_bonus_status,
    get_customer_profile,
    get_recent_transactions,
)
from tools.policy_tools import search_policy_documents
from tools.registry import configure
from tools.ticket_tools import get_ticket_history

__all__ = [
    "configure",
    "get_all_tools",
    "get_bonus_status",
    "get_customer_profile",
    "get_recent_transactions",
    "get_ticket_history",
    "search_policy_documents",
]


def get_all_tools() -> list:
    """Return a list of all available LangChain tools."""
    return [
        get_customer_profile,
        get_recent_transactions,
        get_bonus_status,
        get_ticket_history,
        search_policy_documents,
    ]
