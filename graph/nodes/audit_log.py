"""Node: audit_log - consolidates and summarises the audit trail before
the final response is assembled.

Adds a summary entry with total steps, total duration estimate, and
key decisions made during the pipeline run.
"""

from datetime import datetime, timezone
from typing import Any

from graph.state import GraphState


def audit_log(state: GraphState) -> dict[str, Any]:
    """Append a summary audit entry before final response.

    Collects key decisions from the trail and adds a consolidated
    summary entry.
    """
    trail = state.get("audit_trail", [])
    classification = state.get("classification", {})
    risk = state.get("risk_assessment", {})
    draft = state.get("draft_response", {})
    gc = state.get("groundedness_check", {})

    summary = {
        "step": "audit_log",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_steps": len(trail) + 1,
        "category": classification.get("category", "unknown"),
        "risk_level": risk.get("risk_level", "unknown"),
        "requires_human_review": risk.get("requires_human_review", False),
        "groundedness": gc.get("is_grounded", None),
        "draft_retries": state.get("draft_retries", 0),
        "approval_required": draft.get("approval_required", False),
        "tone": draft.get("tone", "unknown"),
    }

    return {
        "audit_trail": trail + [summary],
    }
