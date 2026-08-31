"""Separation evaluators - check that draft responses and internal
recommendations stay in their lanes.

The draft (what to SAY) should be customer-safe.
The recommendation (what to DO) should be an internal action.
Neither should claim unconfirmed actions.
"""

from typing import Any

# Phrases that should NOT appear in a customer-facing draft
_FORBIDDEN_DRAFT_PHRASES = [
    "i have escalated",
    "your case has been escalated",
    "we have forwarded",
    "compliance has been notified",
    "your ticket has been created",
    "the team has been informed",
    "we have already",
    "action has been taken",
]

# Phrases that indicate internal-only language (wrong in a draft)
_INTERNAL_LANGUAGE = [
    "check the queue",
    "check verification queue",
    "escalation ticket",
    "internal review",
    "tier 2",
    "tier 3",
]

# Phrases that indicate unconfirmed-action claims
_UNCONFIRMED_ACTION_PHRASES = [
    "has been escalated",
    "has been created",
    "has been forwarded",
    "has been submitted",
    "has been notified",
    "has already been",
]


def eval_draft_is_customer_safe(result: dict[str, Any]) -> dict[str, Any]:
    """Check that the draft response does not contain internal or
    unconfirmed-action language."""
    draft = result.get("final_output", {}).get("draft_response", {})
    text = draft.get("customer_message", "").lower()

    issues: list[str] = []

    for phrase in _FORBIDDEN_DRAFT_PHRASES:
        if phrase in text:
            issues.append(f"Draft contains forbidden phrase: '{phrase}'")

    for phrase in _INTERNAL_LANGUAGE:
        if phrase in text:
            issues.append(f"Draft contains internal language: '{phrase}'")

    return {
        "is_safe": len(issues) == 0,
        "score": 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.25),
        "issues": issues,
    }


def eval_recommendation_is_internal_action(result: dict[str, Any]) -> dict[str, Any]:
    """Check that the recommendation is an internal action, not customer text."""
    rec = result.get("final_output", {}).get("recommendation", {})
    action = rec.get("recommended_action", "").lower()

    issues: list[str] = []

    # Should contain action-oriented language
    action_verbs = ["check", "verify", "escalate", "review", "confirm", "flag", "investigate"]
    has_action = any(v in action for v in action_verbs)
    if not has_action:
        issues.append("Recommendation lacks action verbs (check, verify, escalate, etc.)")

    # Should not look like a customer email
    if "dear " in action or "thank you for" in action or "we apologize" in action:
        issues.append("Recommendation looks like customer-facing text, not an internal action")

    return {
        "is_internal": len(issues) == 0,
        "score": 1.0 if not issues else 0.5,
        "issues": issues,
    }


def eval_no_unconfirmed_actions(result: dict[str, Any]) -> dict[str, Any]:
    """Check that neither output claims actions have already been taken."""
    draft = result.get("final_output", {}).get("draft_response", {})
    rec = result.get("final_output", {}).get("recommendation", {})

    draft_text = draft.get("customer_message", "").lower()
    rec_text = rec.get("recommended_action", "").lower() + " " + rec.get("reason", "").lower()

    issues: list[str] = []

    for phrase in _UNCONFIRMED_ACTION_PHRASES:
        if phrase in draft_text:
            issues.append(f"Draft claims unconfirmed action: '{phrase}'")
        if phrase in rec_text:
            issues.append(f"Recommendation claims unconfirmed action: '{phrase}'")

    return {
        "no_unconfirmed": len(issues) == 0,
        "score": 1.0 if not issues else max(0.0, 1.0 - len(issues) * 0.3),
        "issues": issues,
    }


def eval_missing_info_quality(result: dict[str, Any]) -> dict[str, Any]:
    """Check that missing_information is populated and specific."""
    rec = result.get("final_output", {}).get("recommendation", {})
    missing = rec.get("missing_information", [])

    if not missing:
        return {
            "has_missing_info": False,
            "score": 0.5,
            "issues": ["missing_information is empty - should list what's still needed"],
        }

    # Check for generic placeholders
    generic = [m for m in missing if len(m) < 5 or m in ("unknown", "none", "n/a", "tbd")]
    if generic:
        return {
            "has_missing_info": True,
            "score": 0.7,
            "issues": [f"Generic missing_information entries: {generic}"],
        }

    return {
        "has_missing_info": True,
        "score": 1.0,
        "issues": [],
    }


def eval_approval_correctness(expected: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Check that approval_required matches the expected review decision."""
    expected_review = expected.get("expected_human_review", False)

    draft = result.get("final_output", {}).get("draft_response", {})
    actual_approval = draft.get("approval_required", False)

    risk = result.get("final_output", {}).get("risk_assessment", {})
    actual_review = risk.get("requires_human_review", False)

    needs_approval = actual_approval or actual_review

    if expected_review and not needs_approval:
        return {"correct": False, "score": 0.0, "issues": ["Expected human review but none required"]}
    if not expected_review and needs_approval:
        return {"correct": False, "score": 0.5, "issues": ["Unexpected human review flag (conservative, not wrong)"]}

    return {"correct": True, "score": 1.0, "issues": []}


def evaluate_separation(expected: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Run all 5 separation evaluators and return aggregate."""
    checks = {
        "draft_is_customer_safe": eval_draft_is_customer_safe(result),
        "recommendation_is_internal": eval_recommendation_is_internal_action(result),
        "no_unconfirmed_actions": eval_no_unconfirmed_actions(result),
        "missing_info_quality": eval_missing_info_quality(result),
        "approval_correctness": eval_approval_correctness(expected, result),
    }

    scores = [c["score"] for c in checks.values()]
    aggregate = sum(scores) / len(scores) if scores else 0.0

    return {
        "checks": checks,
        "aggregate": round(aggregate, 3),
    }
