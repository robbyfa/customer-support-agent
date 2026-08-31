"""Pydantic model for the draft customer-facing response."""

from typing import Literal

from pydantic import BaseModel, Field


class DraftResponse(BaseModel):
    """Proposed customer-facing message produced by the response chain.

    Must be reviewed (and possibly approved) before being sent.
    """

    customer_message: str = Field(
        description="The draft message to send to the customer."
    )

    tone: Literal["neutral", "empathetic", "formal"] = Field(
        description="The emotional tone used in the response."
    )

    should_send: bool = Field(
        description="Whether this response is ready to send as-is."
    )

    approval_required: bool = Field(
        description="Whether human approval is needed before sending."
    )

    reason_approval_required: str | None = Field(
        default=None,
        description="Explanation of why approval is required, if applicable.",
    )

    def format_text(self) -> str:
        """Render a human-readable summary of the draft response."""
        lines = [
            f"Tone: {self.tone}",
            f"Approval required: {'Yes' if self.approval_required else 'No'}",
        ]
        if self.reason_approval_required:
            lines.append(f"Reason: {self.reason_approval_required}")
        lines.append("")
        lines.append(self.customer_message)
        return "\n".join(lines)
