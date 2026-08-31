"""Tests for the evaluation framework.

Covers dataset validation, individual evaluators, and aggregate scoring.
No LLM calls - all tests use mock results.
"""

import pytest

from evals.dataset import get_by_category, get_by_expected_review, get_dataset
from evals.evaluators import (
    WEIGHTS,
    eval_classification,
    eval_keywords,
    eval_policy_retrieval,
    eval_response_quality,
    eval_sensitivity,
    evaluate_response,
)


# ---------------------------------------------------------------------------
# Dataset validation
# ---------------------------------------------------------------------------


class TestDataset:
    def test_has_25_cases(self):
        assert len(get_dataset()) == 25

    def test_all_ids_unique(self):
        ids = [c["id"] for c in get_dataset()]
        assert len(ids) == len(set(ids))

    def test_all_required_fields(self):
        required = {
            "id", "customer_message", "customer_id",
            "expected_category", "expected_human_review",
            "must_include", "must_not_include",
        }
        for case in get_dataset():
            assert required.issubset(case.keys()), f"Missing fields in {case['id']}"

    def test_all_six_categories_covered(self):
        categories = {c["expected_category"] for c in get_dataset()}
        expected = {
            "withdrawal_issue", "deposit_issue", "login_issue",
            "bonus_issue", "account_verification", "responsible_gaming",
        }
        assert expected.issubset(categories)

    def test_get_by_category(self):
        withdrawal = get_by_category("withdrawal_issue")
        assert len(withdrawal) >= 3
        assert all(c["expected_category"] == "withdrawal_issue" for c in withdrawal)

    def test_get_by_expected_review(self):
        review_cases = get_by_expected_review(True)
        assert len(review_cases) >= 5
        assert all(c["expected_human_review"] is True for c in review_cases)

    def test_get_by_expected_no_review(self):
        no_review = get_by_expected_review(False)
        assert len(no_review) >= 5


# ---------------------------------------------------------------------------
# Mock result helpers
# ---------------------------------------------------------------------------


def _mock_result(
    category="withdrawal_issue",
    urgency="high",
    sentiment="negative",
    sensitive_case=False,
    requires_human_review=True,
    policy_sources=None,
    draft_message="We are investigating your issue.",
    summary="Customer reports failed withdrawal.",
):
    """Build a mock graph result for evaluator testing."""
    return {
        "final_output": {
            "classification": {
                "category": category,
                "urgency": urgency,
                "sentiment": sentiment,
                "sensitive_case": sensitive_case,
                "summary": summary,
            },
            "risk_assessment": {
                "requires_human_review": requires_human_review,
            },
            "draft_response": {
                "customer_message": draft_message,
            },
        },
        "audit_trail": [
            {
                "step": "retrieve_policy",
                "sources": policy_sources or ["withdrawal_policy.md"],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Classification evaluator
# ---------------------------------------------------------------------------


class TestEvalClassification:
    def test_perfect_match(self):
        expected = {"expected_category": "withdrawal_issue", "expected_urgency": "high", "expected_sentiment": "negative"}
        result = _mock_result()
        assert eval_classification(expected, result) == pytest.approx(1.0, abs=0.01)

    def test_category_only(self):
        expected = {"expected_category": "withdrawal_issue", "expected_urgency": "low", "expected_sentiment": "positive"}
        result = _mock_result()
        assert eval_classification(expected, result) == pytest.approx(1 / 3, abs=0.01)

    def test_zero_match(self):
        expected = {"expected_category": "bonus_issue", "expected_urgency": "low", "expected_sentiment": "positive"}
        result = _mock_result()
        assert eval_classification(expected, result) == 0.0


# ---------------------------------------------------------------------------
# Policy retrieval evaluator
# ---------------------------------------------------------------------------


class TestEvalPolicyRetrieval:
    def test_correct_source(self):
        expected = {"expected_policy_source": "withdrawal_policy.md"}
        result = _mock_result(policy_sources=["withdrawal_policy.md"])
        assert eval_policy_retrieval(expected, result) == 1.0

    def test_wrong_source(self):
        expected = {"expected_policy_source": "bonus_policy.md"}
        result = _mock_result(policy_sources=["withdrawal_policy.md"])
        assert eval_policy_retrieval(expected, result) == 0.0

    def test_no_expected_source(self):
        expected = {"expected_policy_source": None}
        result = _mock_result()
        assert eval_policy_retrieval(expected, result) == 1.0


# ---------------------------------------------------------------------------
# Sensitivity evaluator
# ---------------------------------------------------------------------------


class TestEvalSensitivity:
    def test_correctly_flagged(self):
        expected = {"expected_human_review": True}
        result = _mock_result(requires_human_review=True)
        assert eval_sensitivity(expected, result) == 1.0

    def test_missed_flag(self):
        expected = {"expected_human_review": True}
        result = _mock_result(requires_human_review=False)
        assert eval_sensitivity(expected, result) == 0.0

    def test_correctly_not_flagged(self):
        expected = {"expected_human_review": False}
        result = _mock_result(requires_human_review=False)
        assert eval_sensitivity(expected, result) == 1.0

    def test_false_positive(self):
        expected = {"expected_human_review": False}
        result = _mock_result(requires_human_review=True)
        assert eval_sensitivity(expected, result) == 0.0


# ---------------------------------------------------------------------------
# Response quality evaluator
# ---------------------------------------------------------------------------


class TestEvalResponseQuality:
    def test_all_keywords_present(self):
        expected = {"must_include": ["failed", "withdrawal"], "must_not_include": []}
        result = _mock_result(draft_message="We see your failed withdrawal attempts.")
        assert eval_response_quality(expected, result) == 1.0

    def test_partial_keywords(self):
        expected = {"must_include": ["failed", "withdrawal"], "must_not_include": []}
        result = _mock_result(draft_message="We see your failed attempts.")
        assert eval_response_quality(expected, result) == 0.5

    def test_forbidden_keyword_penalty(self):
        expected = {"must_include": [], "must_not_include": ["resolved"]}
        result = _mock_result(draft_message="Your withdrawal is resolved.")
        assert eval_response_quality(expected, result) == 0.5

    def test_no_keywords(self):
        expected = {"must_include": [], "must_not_include": []}
        result = _mock_result()
        assert eval_response_quality(expected, result) == 1.0


# ---------------------------------------------------------------------------
# Keywords evaluator
# ---------------------------------------------------------------------------


class TestEvalKeywords:
    def test_summary_contains_keywords(self):
        expected = {"must_include": ["failed", "withdrawal"]}
        result = _mock_result(summary="Customer reports failed withdrawal attempts.")
        assert eval_keywords(expected, result) == 1.0

    def test_summary_missing_keywords(self):
        expected = {"must_include": ["bonus", "expired"]}
        result = _mock_result(summary="Customer reports failed withdrawal.")
        assert eval_keywords(expected, result) == 0.0

    def test_no_keywords_expected(self):
        expected = {"must_include": []}
        result = _mock_result()
        assert eval_keywords(expected, result) == 1.0


# ---------------------------------------------------------------------------
# Aggregate scoring
# ---------------------------------------------------------------------------


class TestAggregateScoring:
    def test_weights_sum_to_one(self):
        assert sum(WEIGHTS.values()) == pytest.approx(1.0)

    def test_perfect_score(self):
        expected = {
            "expected_category": "withdrawal_issue",
            "expected_urgency": "high",
            "expected_sentiment": "negative",
            "expected_human_review": True,
            "expected_policy_source": "withdrawal_policy.md",
            "must_include": ["failed", "withdrawal"],
            "must_not_include": [],
        }
        result = _mock_result(
            draft_message="We see your failed withdrawal issue.",
            summary="Customer reports failed withdrawal.",
        )
        scores = evaluate_response(expected, result)
        assert scores["aggregate"] == pytest.approx(1.0, abs=0.01)

    def test_aggregate_has_all_keys(self):
        expected = {
            "expected_category": "other",
            "expected_urgency": "low",
            "expected_sentiment": "neutral",
            "expected_human_review": False,
            "expected_policy_source": None,
            "must_include": [],
            "must_not_include": [],
        }
        result = _mock_result(category="other", urgency="low", sentiment="neutral", requires_human_review=False)
        scores = evaluate_response(expected, result)
        assert "classification" in scores
        assert "retrieval" in scores
        assert "sensitivity" in scores
        assert "response_quality" in scores
        assert "keywords" in scores
        assert "aggregate" in scores

    def test_aggregate_bounded_0_to_1(self):
        expected = {
            "expected_category": "bonus_issue",
            "expected_urgency": "low",
            "expected_sentiment": "positive",
            "expected_human_review": False,
            "expected_policy_source": "bonus_policy.md",
            "must_include": ["bonus"],
            "must_not_include": ["resolved"],
        }
        result = _mock_result()
        scores = evaluate_response(expected, result)
        assert 0.0 <= scores["aggregate"] <= 1.0
