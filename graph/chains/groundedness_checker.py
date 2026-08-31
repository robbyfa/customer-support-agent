"""Groundedness checker chain - verifies that a draft response is
grounded in the provided policy context.
"""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class GroundednessCheck(BaseModel):
    """Result of checking whether a response is grounded in policy."""

    is_grounded: bool = Field(
        description="Whether the response is fully supported by the policy context."
    )

    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )

    issues: list[str] = Field(
        default_factory=list,
        description="List of statements in the response not supported by policy.",
    )


_SYSTEM_PROMPT = """\
You are a quality assurance reviewer. Your job is to check whether a \
draft customer support response is grounded in the provided policy documents.

A response is "grounded" if every factual claim and instruction it contains \
is supported by the policy context. Opinions, empathy statements, and \
standard politeness do not need grounding.

Check the draft response against the policy context and report:
- is_grounded: true if all factual claims are supported, false otherwise.
- confidence: how confident you are in your assessment (0.0 to 1.0).
- issues: list any specific statements that are not supported by policy."""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Policy context:\n{policy_context}\n\n"
            "Draft response:\n{draft_response}",
        ),
    ]
)


def get_groundedness_chain():
    """Build and return the groundedness checking chain.

    Deferred so the LLM is only instantiated when actually needed.
    """
    llm = ChatOpenAI(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        temperature=0,
    )
    return _prompt | llm.with_structured_output(GroundednessCheck)
