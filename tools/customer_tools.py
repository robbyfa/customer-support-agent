"""Customer-related LangChain tools.

These are read-only tools that retrieve customer profile data,
recent transactions, and bonus status from the mock data layer.
"""

from langchain_core.tools import tool

from storage.mock_data import (
    get_customer,
    get_customer_bonus,
    get_customer_transactions,
)


@tool
def get_customer_profile(customer_id: str) -> dict:
    """Look up a customer profile by their ID (e.g. CUST-1001).

    Returns the full customer record including account status,
    verification status, risk level, and responsible gaming flags.
    Returns an error message if the customer is not found.
    """
    customer = get_customer(customer_id)
    if customer is None:
        return {"error": f"Customer {customer_id} not found"}
    return customer


@tool
def get_recent_transactions(customer_id: str) -> dict:
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


@tool
def get_bonus_status(customer_id: str) -> dict:
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
