"""Response generator chain - drafts a customer-facing response grounded
in policy context, customer data, and risk assessment.
"""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from models.response import DraftResponse

_SYSTEM_PROMPT = """\
You are a senior customer support agent for an online sports betting and \
gaming company. Your job is to draft a response to the customer based on \
the information provided.

You will receive:
- The original customer message
- The ticket classification (category, urgency, sentiment)
- Relevant policy extracts
- Customer context (profile, transactions, tickets, bonuses, flags)
- Risk assessment (risk level, whether human review is required)

Guidelines:
- Be empathetic if the customer sentiment is negative.
- Use a formal tone for high-risk or sensitive cases.
- Use a neutral tone for standard inquiries.
- Ground your response in the provided policy context - do not invent policies.
- Never tell the customer an issue is resolved unless confirmed.
- If human review is required, acknowledge that the case is being escalated.
- Keep the response concise, professional, and actionable.
- If information is missing, note what is still needed.
- Set approval_required=true if the risk assessment requires human review \
or if the case is sensitive."""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Customer message: {customer_message}\n\n"
            "Classification: {classification}\n\n"
            "Policy context:\n{policy_context}\n\n"
            "Customer context: {customer_context}\n\n"
            "Risk assessment: {risk_assessment}",
        ),
    ]
)


def get_response_chain():
    """Build and return the response generation chain.

    Deferred so the LLM is only instantiated when actually needed.
    """
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=0.3,
    )
    return _prompt | llm.with_structured_output(DraftResponse)
