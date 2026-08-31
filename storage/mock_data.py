"""Mock data loading layer for the Customer Support Resolution Copilot.

Loads JSON fixtures from data/mock/ and provides lookup helpers
used by tools and graph nodes.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "mock"


# ---------------------------------------------------------------------------
# Raw loaders (cached so the files are only read once per process)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_customers() -> list[dict[str, Any]]:
    """Load all customer records."""
    with open(_DATA_DIR / "customers.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_tickets() -> list[dict[str, Any]]:
    """Load all ticket records."""
    with open(_DATA_DIR / "tickets.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_transactions() -> list[dict[str, Any]]:
    """Load all transaction records."""
    with open(_DATA_DIR / "transactions.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_bonus_history() -> list[dict[str, Any]]:
    """Load all bonus history records."""
    with open(_DATA_DIR / "bonus_history.json") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def get_customer(customer_id: str) -> dict[str, Any] | None:
    """Return a single customer by ID, or None if not found."""
    for customer in load_customers():
        if customer["customer_id"] == customer_id:
            return customer
    return None


def get_customer_transactions(customer_id: str) -> list[dict[str, Any]]:
    """Return all transactions for a given customer ID."""
    return [
        txn for txn in load_transactions() if txn["customer_id"] == customer_id
    ]


def get_customer_tickets(customer_id: str) -> list[dict[str, Any]]:
    """Return all tickets for a given customer ID."""
    return [
        ticket for ticket in load_tickets() if ticket["customer_id"] == customer_id
    ]


def get_customer_bonus(customer_id: str) -> list[dict[str, Any]]:
    """Return all bonus records for a given customer ID."""
    return [
        bonus
        for bonus in load_bonus_history()
        if bonus["customer_id"] == customer_id
    ]
