"""Classification chain — classifies a customer support message into
a structured TicketClassification using an LLM with structured output.
"""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from models.classification import TicketClassification

_SYSTEM_PROMPT = """\
You are a customer support triage specialist for an online sports betting \
and gaming company. Your job is to classify incoming customer messages.

Analyse the message and produce a structured classification with:
- category: one of withdrawal_issue, deposit_issue, login_issue, \
bonus_issue, account_verification, responsible_gaming, other.
- urgency: low, medium, or high.
- sentiment: positive, neutral, or negative.
- summary: a one-sentence summary of the issue.
- requires_human_review: true if the case is sensitive, high-risk, \
involves responsible gaming, repeated failures, or complaints.
- sensitive_case: true if the issue involves responsible gaming, \
potential fraud, account compromise, or self-exclusion.
- extracted_customer_id: the customer ID if mentioned in the message \
(e.g. CUST-1001), otherwise null.

Be precise. Do not guess a category — use "other" if it does not fit."""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "{customer_message}"),
    ]
)


def get_classification_chain():
    """Build and return the classification chain.

    Deferred so the LLM is only instantiated when actually needed
    (avoids import-time errors when OPENAI_API_KEY is not set).
    """
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=0,
    )
    return _prompt | llm.with_structured_output(TicketClassification)
