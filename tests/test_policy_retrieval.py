"""Tests for policy document ingestion and RAG retrieval.

Verifies that the PolicyVectorStore correctly ingests policy markdown
files and returns relevant results for semantic search queries.
"""

import pytest

from storage.vector_store import PolicyVectorStore


@pytest.fixture(scope="module")
def store() -> PolicyVectorStore:
    """Shared ephemeral vector store ingested once for the module."""
    vs = PolicyVectorStore(collection_name="test_policies")
    vs.ingest_policies()
    return vs


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class TestIngestion:
    def test_ingest_returns_positive_chunk_count(self):
        vs = PolicyVectorStore(collection_name="test_ingest")
        count = vs.ingest_policies()
        assert count > 0

    def test_all_seven_policies_ingested(self, store: PolicyVectorStore):
        """Every policy file should have at least one chunk in the store."""
        results = store.search("policy", n_results=50)
        sources = {r["source"] for r in results}
        expected = {
            "withdrawal_policy.md",
            "deposit_policy.md",
            "bonus_policy.md",
            "login_policy.md",
            "account_verification_policy.md",
            "responsible_gaming_policy.md",
            "escalation_policy.md",
        }
        assert expected.issubset(sources), f"Missing: {expected - sources}"


# ---------------------------------------------------------------------------
# Search relevance
# ---------------------------------------------------------------------------


class TestSearchRelevance:
    def test_failed_withdrawal_returns_withdrawal_policy(
        self, store: PolicyVectorStore
    ):
        results = store.search("failed withdrawal")
        top_sources = [r["source"] for r in results]
        assert "withdrawal_policy.md" in top_sources

    def test_self_exclusion_returns_responsible_gaming(
        self, store: PolicyVectorStore
    ):
        results = store.search("self-exclusion request")
        top_sources = [r["source"] for r in results]
        assert "responsible_gaming_policy.md" in top_sources

    def test_deposit_not_credited_returns_deposit_policy(
        self, store: PolicyVectorStore
    ):
        results = store.search("deposit not credited to my account")
        top_sources = [r["source"] for r in results]
        assert "deposit_policy.md" in top_sources

    def test_bonus_wagering_returns_bonus_policy(
        self, store: PolicyVectorStore
    ):
        results = store.search("bonus wagering requirements not met")
        top_sources = [r["source"] for r in results]
        assert "bonus_policy.md" in top_sources

    def test_account_locked_returns_login_policy(
        self, store: PolicyVectorStore
    ):
        results = store.search("account locked cannot log in")
        top_sources = [r["source"] for r in results]
        assert "login_policy.md" in top_sources

    def test_verification_pending_returns_verification_policy(
        self, store: PolicyVectorStore
    ):
        results = store.search("identity verification documents pending")
        top_sources = [r["source"] for r in results]
        assert "account_verification_policy.md" in top_sources

    def test_escalation_returns_escalation_policy(
        self, store: PolicyVectorStore
    ):
        results = store.search("escalate to specialist team tier")
        top_sources = [r["source"] for r in results]
        assert "escalation_policy.md" in top_sources


# ---------------------------------------------------------------------------
# Search result structure
# ---------------------------------------------------------------------------


class TestSearchResultStructure:
    def test_result_has_expected_keys(self, store: PolicyVectorStore):
        results = store.search("withdrawal")
        assert len(results) > 0
        for r in results:
            assert "content" in r
            assert "source" in r
            assert "chunk_index" in r
            assert "score" in r

    def test_score_is_between_zero_and_one(self, store: PolicyVectorStore):
        results = store.search("deposit processing time")
        for r in results:
            assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_collection(self):
        vs = PolicyVectorStore(collection_name="test_reset")
        vs.ingest_policies()
        results_before = vs.search("withdrawal")
        assert len(results_before) > 0

        vs.reset()
        results_after = vs.search("withdrawal", n_results=1)
        assert len(results_after) == 0


# ===========================================================================
# retrieve_policy node tests (Task 6)
# ===========================================================================

from tools.registry import configure
from graph.nodes.retrieve_policy import retrieve_policy


@pytest.fixture(scope="module")
def _configure_registry(store: PolicyVectorStore):
    """Register the shared store so the node can find it."""
    configure(store)


@pytest.mark.usefixtures("_configure_registry")
class TestRetrievePolicyNode:
    def test_withdrawal_issue_returns_withdrawal_policy(self):
        state = {
            "classification": {
                "category": "withdrawal_issue",
                "summary": "Customer reports multiple failed withdrawal attempts.",
            },
            "audit_trail": [],
        }
        result = retrieve_policy(state)

        assert "policy_context" in result
        assert len(result["policy_context"]) > 0
        # At least one chunk should come from the withdrawal policy
        combined = " ".join(result["policy_context"]).lower()
        assert "withdrawal" in combined

    def test_responsible_gaming_returns_responsible_gaming_policy(self):
        state = {
            "classification": {
                "category": "responsible_gaming",
                "summary": "Customer requests self-exclusion period.",
            },
            "audit_trail": [],
        }
        result = retrieve_policy(state)

        combined = " ".join(result["policy_context"]).lower()
        assert "self-exclusion" in combined or "responsible gaming" in combined

    def test_audit_trail_appended(self):
        state = {
            "classification": {
                "category": "deposit_issue",
                "summary": "Deposit not credited.",
            },
            "audit_trail": [{"step": "classify_ticket"}],
        }
        result = retrieve_policy(state)

        trail = result["audit_trail"]
        assert len(trail) == 2
        assert trail[1]["step"] == "retrieve_policy"
        assert "sources" in trail[1]
        assert "chunks_retrieved" in trail[1]

    def test_empty_classification_still_returns_results(self):
        state = {
            "classification": {},
            "audit_trail": [],
        }
        result = retrieve_policy(state)
        # Should fall back to a generic query and still return chunks
        assert len(result["policy_context"]) > 0

    def test_policy_context_contains_strings(self):
        state = {
            "classification": {
                "category": "login_issue",
                "summary": "Account locked after failed logins.",
            },
            "audit_trail": [],
        }
        result = retrieve_policy(state)
        for chunk in result["policy_context"]:
            assert isinstance(chunk, str)
            assert len(chunk) > 0
