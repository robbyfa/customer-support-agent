"""Pydantic model for the policy-grounded support recommendation."""

from pydantic import BaseModel, Field


class SupportRecommendation(BaseModel):
    """Internal recommendation for the support agent, grounded in policy.

    Produced by the response generation chain and consumed by the
    draft_response node and approval gate.
    """

    recommended_action: str = Field(
        description="The specific action the support agent should take."
    )

    reason: str = Field(
        description="Why this action is recommended, referencing policy or context."
    )

    relevant_policy_sources: list[str] = Field(
        default_factory=list,
        description="Policy document filenames that support this recommendation.",
    )

    missing_information: list[str] = Field(
        default_factory=list,
        description="Any information still needed to fully resolve the case.",
    )

    human_review_required: bool = Field(
        description="Whether this recommendation needs human approval before acting."
    )
