"""Tests for the mock data loading layer (storage/mock_data.py).

Covers: record counts, known-customer lookups, unknown-customer handling,
and per-customer filtering for transactions, tickets, and bonuses.
"""

from storage.mock_data import (
    get_customer,
    get_customer_bonus,
    get_customer_tickets,
    get_customer_transactions,
    load_bonus_history,
    load_customers,
    load_tickets,
    load_transactions,
)


# ---------------------------------------------------------------------------
# Record counts
# ---------------------------------------------------------------------------


class TestRecordCounts:
    def test_customer_count(self):
        assert len(load_customers()) == 6

    def test_ticket_count(self):
        assert len(load_tickets()) == 10

    def test_transaction_count(self):
        assert len(load_transactions()) == 14

    def test_bonus_count(self):
        assert len(load_bonus_history()) == 5


# ---------------------------------------------------------------------------
# Customer lookup
# ---------------------------------------------------------------------------


class TestCustomerLookup:
    def test_known_customer_returns_dict(self):
        customer = get_customer("CUST-1001")
        assert customer is not None
        assert customer["customer_id"] == "CUST-1001"
        assert customer["name"] == "Maria Gonzalez"

    def test_known_customer_fields(self):
        customer = get_customer("CUST-1001")
        expected_keys = {
            "customer_id",
            "name",
            "email",
            "account_status",
            "verification_status",
            "risk_level",
            "recent_failed_withdrawals",
            "active_bonus",
            "responsible_gaming_flag",
            "registered_date",
            "country",
            "notes",
        }
        assert expected_keys.issubset(customer.keys())

    def test_unknown_customer_returns_none(self):
        assert get_customer("CUST-9999") is None

    def test_empty_string_returns_none(self):
        assert get_customer("") is None

    def test_all_six_customers_exist(self):
        for cid in [
            "CUST-1001",
            "CUST-1002",
            "CUST-1003",
            "CUST-1004",
            "CUST-1005",
            "CUST-1006",
        ]:
            assert get_customer(cid) is not None, f"{cid} should exist"


# ---------------------------------------------------------------------------
# Per-customer transactions
# ---------------------------------------------------------------------------


class TestCustomerTransactions:
    def test_cust_1001_has_five_transactions(self):
        txns = get_customer_transactions("CUST-1001")
        assert len(txns) == 5

    def test_cust_1001_failed_withdrawals(self):
        txns = get_customer_transactions("CUST-1001")
        failed = [
            t for t in txns if t["type"] == "withdrawal" and t["status"] == "failed"
        ]
        assert len(failed) == 3

    def test_unknown_customer_returns_empty_list(self):
        assert get_customer_transactions("CUST-9999") == []


# ---------------------------------------------------------------------------
# Per-customer tickets
# ---------------------------------------------------------------------------


class TestCustomerTickets:
    def test_cust_1001_has_three_tickets(self):
        tickets = get_customer_tickets("CUST-1001")
        assert len(tickets) == 3

    def test_cust_1006_has_one_ticket(self):
        tickets = get_customer_tickets("CUST-1006")
        assert len(tickets) == 1
        assert tickets[0]["category"] == "responsible_gaming"

    def test_unknown_customer_returns_empty_list(self):
        assert get_customer_tickets("CUST-9999") == []


# ---------------------------------------------------------------------------
# Per-customer bonus history
# ---------------------------------------------------------------------------


class TestCustomerBonus:
    def test_cust_1004_has_active_bonus(self):
        bonuses = get_customer_bonus("CUST-1004")
        assert len(bonuses) == 1
        assert bonuses[0]["status"] == "active"
        assert bonuses[0]["bonus_code"] == "WELCOME100"

    def test_cust_1005_has_no_bonus(self):
        assert get_customer_bonus("CUST-1005") == []

    def test_unknown_customer_returns_empty_list(self):
        assert get_customer_bonus("CUST-9999") == []
