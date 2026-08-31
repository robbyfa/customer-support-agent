"""Recommendation generator chain - produces an internal action
recommendation for the support agent, separate from the customer-facing draft.

This tells the agent what to DO (escalate, check queue, create ticket),
while the draft response tells them what to SAY to the customer.
"""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from models.recommendation import SupportRecommendation

_SYSTEM_PROMPT = """\
You are an internal support operations advisor. Your job is to recommend \
the specific ACTIONS a support agent should take for this case. This is \
NOT the customer-facing response - this is the internal playbook.

You will receive the ticket classification, policy context, customer context, \
and risk assessment.

Produce a structured recommendation with:
- recommended_action: the specific internal action(s) the agent should take. \
Examples: "Escalate to Payments Operations", "Check verification queue and \
confirm document status", "Flag for Responsible Gaming team review", \
"No action needed - standard inquiry". Be specific and actionable.
- reason: why this action is appropriate, referencing policy or customer data.
- relevant_policy_sources: which policy documents support this recommendation.
- missing_information: what data the agent still needs to collect or verify \
before the case can be fully resolved. Be specific - e.g. "payment provider \
error details", "verification queue status", not generic placeholders.
- human_review_required: whether a human must approve before executing.

Focus on the INTERNAL workflow, not what to say to the customer."""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Classification: {classification}\n\n"
            "Policy context:\n{policy_context}\n\n"
            "Customer context: {customer_context}\n\n"
            "Risk assessment: {risk_assessment}",
        ),
    ]
)


def get_recommendation_chain():
    """Build and return the recommendation generation chain.

    Deferred so the LLM is only instantiated when actually needed.
    """
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=0,
    )
    return _prompt | llm.with_structured_output(SupportRecommendation)
