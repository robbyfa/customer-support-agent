"""Evaluators for the Customer Support Resolution Copilot.

Five evaluation dimensions with a weighted aggregate scorer.
"""

from typing import Any


# ---------------------------------------------------------------------------
# 1. Classification accuracy (0.25)
# ---------------------------------------------------------------------------


def eval_classification(expected: dict[str, Any], result: dict[str, Any]) -> float:
    """Score how well the classification matches expectations.

    Checks category, urgency, and sentiment. Each correct field = 1/3.
    """
    classification = result.get("final_output", {}).get("classification", {})

    score = 0.0
    if classification.get("category") == expected.get("expected_category"):
        score += 1 / 3
    if classification.get("urgency") == expected.get("expected_urgency"):
        score += 1 / 3
    if classification.get("sentiment") == expected.get("expected_sentiment"):
        score += 1 / 3

    return round(min(score, 1.0), 3)


# ---------------------------------------------------------------------------
# 2. Policy retrieval relevance (0.20)
# ---------------------------------------------------------------------------


def eval_policy_retrieval(expected: dict[str, Any], result: dict[str, Any]) -> float:
    """Score whether the correct policy document was retrieved.

    1.0 if expected source appears in audit trail sources, 0.0 otherwise.
    Returns 1.0 if no policy source is expected (e.g. 'other' category).
    """
    expected_source = expected.get("expected_policy_source")
    if expected_source is None:
        return 1.0

    trail = result.get("audit_trail", [])
    for entry in trail:
        if entry.get("step") == "retrieve_policy":
            sources = entry.get("sources", [])
            if expected_source in sources:
                return 1.0

    return 0.0


# ---------------------------------------------------------------------------
# 3. Sensitive-case detection (0.20)
# ---------------------------------------------------------------------------


def eval_sensitivity(expected: dict[str, Any], result: dict[str, Any]) -> float:
    """Score whether human review was correctly flagged.

    1.0 if the actual review decision matches expected, 0.0 otherwise.
    """
    expected_review = expected.get("expected_human_review", False)

    risk = result.get("final_output", {}).get("risk_assessment", {})
    actual_review = risk.get("requires_human_review", False)

    classification = result.get("final_output", {}).get("classification", {})
    actual_sensitive = classification.get("sensitive_case", False)

    # Match on either the risk review flag or sensitive_case
    if expected_review:
        return 1.0 if (actual_review or actual_sensitive) else 0.0
    else:
        return 1.0 if not actual_review else 0.0


# ---------------------------------------------------------------------------
# 4. Response quality - keyword presence (0.20)
# ---------------------------------------------------------------------------


def eval_response_quality(expected: dict[str, Any], result: dict[str, Any]) -> float:
    """Score response quality based on must_include and must_not_include keywords.

    Each must_include keyword found = proportional credit.
    Any must_not_include keyword found = penalty of 0.5.
    """
    draft = result.get("final_output", {}).get("draft_response", {})
    response_text = draft.get("customer_message", "").lower()

    must_include = [k.lower() for k in expected.get("must_include", [])]
    must_not_include = [k.lower() for k in expected.get("must_not_include", [])]

    # Inclusion score
    if must_include:
        found = sum(1 for k in must_include if k in response_text)
        inclusion_score = found / len(must_include)
    else:
        inclusion_score = 1.0

    # Exclusion penalty
    penalty = 0.0
    for k in must_not_include:
        if k in response_text:
            penalty += 0.5

    return round(max(0.0, min(1.0, inclusion_score - penalty)), 3)


# ---------------------------------------------------------------------------
# 5. Keyword checks - classification summary (0.15)
# ---------------------------------------------------------------------------


def eval_keywords(expected: dict[str, Any], result: dict[str, Any]) -> float:
    """Score whether the classification summary captures key terms.

    Checks must_include keywords against the classification summary.
    """
    classification = result.get("final_output", {}).get("classification", {})
    summary = classification.get("summary", "").lower()

    must_include = [k.lower() for k in expected.get("must_include", [])]

    if not must_include:
        return 1.0

    found = sum(1 for k in must_include if k in summary)
    return round(found / len(must_include), 3)


# ---------------------------------------------------------------------------
# Weighted aggregate
# ---------------------------------------------------------------------------

WEIGHTS = {
    "classification": 0.25,
    "retrieval": 0.20,
    "sensitivity": 0.20,
    "response_quality": 0.20,
    "keywords": 0.15,
}


def evaluate_response(expected: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Run all 5 evaluators and return individual + weighted aggregate scores."""
    scores = {
        "classification": eval_classification(expected, result),
        "retrieval": eval_policy_retrieval(expected, result),
        "sensitivity": eval_sensitivity(expected, result),
        "response_quality": eval_response_quality(expected, result),
        "keywords": eval_keywords(expected, result),
    }

    weighted = sum(scores[k] * WEIGHTS[k] for k in WEIGHTS)
    scores["aggregate"] = round(weighted, 3)

    return scores
