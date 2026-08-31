"""Ticket-related LangChain tools.

Read-only tool for retrieving a customer's support ticket history.
"""

from langchain_core.tools import tool

from storage.mock_data import get_customer, get_customer_tickets


@tool
def get_ticket_history(customer_id: str) -> dict:
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
