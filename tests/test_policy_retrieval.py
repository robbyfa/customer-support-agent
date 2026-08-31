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
