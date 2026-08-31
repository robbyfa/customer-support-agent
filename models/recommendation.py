"""Pydantic model for the policy-grounded support recommendation."""

from pydantic import BaseModel, Field


class SupportRecommendation(BaseModel):
    """Internal action recommendation for the support agent.

    This is the 'what to DO' output - distinct from the customer-facing
    draft response ('what to SAY'). Produced by the recommendation chain
    and consumed by the approval gate.
    """

    action_type: str = Field(
        description=(
            "The type of internal action. Examples: "
            "escalate_to_team, check_queue, verify_identity, "
            "manual_review, no_action_needed."
        )
    )

    recommended_action: str = Field(
        description="The specific action the support agent should take."
    )

    target_team: str = Field(
        default="",
        description=(
            "The team responsible for this action. Examples: "
            "Payments Operations, Compliance, Verification, "
            "Responsible Gaming, Technical, Security."
        ),
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
        description="What data the agent still needs to collect or verify.",
    )

    human_review_required: bool = Field(
        description="Whether this recommendation needs human approval before acting."
    )
