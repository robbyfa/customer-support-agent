"""Suspend reviewable cases until a persisted human decision is supplied."""

from datetime import UTC, datetime
from typing import Any

from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from graph.state import GraphState


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    approved: StrictBool
    reviewer: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)


def approval_gate(state: GraphState) -> dict[str, Any]:
    risk = state.get("risk_assessment") or {}
    draft = state.get("draft_response") or {}
    classification = state.get("classification") or {}
    requires_review = (
        risk.get("requires_human_review", False)
        or draft.get("approval_required", False)
        or classification.get("sensitive_case", False)
    )
    decision = None
    if requires_review:
        # This node restarts on resume. Keep side effects AFTER interrupt.
        response = interrupt({"type": "human_review", "reason": "Support case requires human review"})
        decision = ReviewDecision.model_validate(response)
    approved = decision.approved if decision else True
    entry = {
        "step": "approval_gate",
        "timestamp": datetime.now(UTC).isoformat(),
        "approved": approved,
        "reviewer": decision.reviewer if decision else "system",
        "reason": decision.reason if decision else "Auto-approved - no review flags",
    }
    return {
        "approved": approved,
        "review_decision": decision.model_dump() if decision else None,
        "audit_trail": state.get("audit_trail", []) + [entry],
    }
