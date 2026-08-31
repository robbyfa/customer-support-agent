"""LangGraph workflow for the Customer Support Resolution Copilot.

Flow:
  START → classify_ticket → retrieve_policy → route_by_sensitivity
    ├── sensitive → minimal_customer_context → risk_check
    └── standard → customer_context → risk_check
  risk_check → draft_response → groundedness_check
    ├── grounded       → approval_gate
    ├── not grounded   → draft_response (retry, max 2)
    └── retries exhausted → manual_review_response → approval_gate
  approval_gate → audit_log → final_response → END
"""

from langgraph.graph import END, START, StateGraph

from graph.consts import (
    APPROVAL_GATE,
    AUDIT_LOG,
    CLASSIFY_TICKET,
    CUSTOMER_CONTEXT,
    DRAFT_RESPONSE,
    FINAL_RESPONSE,
    GROUNDEDNESS_CHECK,
    MANUAL_REVIEW_RESPONSE,
    MINIMAL_CUSTOMER_CONTEXT,
    RETRIEVE_POLICY,
    RISK_CHECK,
)
from graph.nodes import (
    approval_gate,
    audit_log,
    classify_ticket,
    draft_response,
    final_response,
    get_customer_context,
    get_minimal_customer_context,
    groundedness_check,
    manual_review_response,
    retrieve_policy,
    risk_check,
)
from graph.nodes.groundedness_check import MAX_RETRIES
from graph.state import GraphState

# ---------------------------------------------------------------------------
# Routing functions
# ---------------------------------------------------------------------------

_SENSITIVE_CATEGORIES = {"responsible_gaming"}


def route_by_category(state: GraphState) -> str:
    """Route after policy retrieval based on issue category.

    - responsible_gaming → minimal context (fast-track sensitive cases)
    - everything else    → full customer context
    """
    classification = state.get("classification", {})
    category = classification.get("category", "other")

    if category in _SENSITIVE_CATEGORIES:
        return MINIMAL_CUSTOMER_CONTEXT

    return CUSTOMER_CONTEXT


def _route_after_groundedness(state: GraphState) -> str:
    """Decide next step after groundedness check.

    - grounded            → approval_gate
    - not grounded, retries left → draft_response (retry)
    - retries exhausted   → manual_review_response (safe fallback)
    """
    check = state.get("groundedness_check", {})
    retries = state.get("draft_retries", 0)

    if check.get("is_grounded", True):
        return APPROVAL_GATE

    if retries >= MAX_RETRIES:
        return MANUAL_REVIEW_RESPONSE

    return DRAFT_RESPONSE


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Build and compile the support copilot graph."""
    graph = StateGraph(GraphState)

    # --- Add nodes ---
    graph.add_node(CLASSIFY_TICKET, classify_ticket)
    graph.add_node(RETRIEVE_POLICY, retrieve_policy)
    graph.add_node(CUSTOMER_CONTEXT, get_customer_context)
    graph.add_node(MINIMAL_CUSTOMER_CONTEXT, get_minimal_customer_context)
    graph.add_node(RISK_CHECK, risk_check)
    graph.add_node(DRAFT_RESPONSE, draft_response)
    graph.add_node(GROUNDEDNESS_CHECK, groundedness_check)
    graph.add_node(MANUAL_REVIEW_RESPONSE, manual_review_response)
    graph.add_node(APPROVAL_GATE, approval_gate)
    graph.add_node(AUDIT_LOG, audit_log)
    graph.add_node(FINAL_RESPONSE, final_response)

    # --- Entry ---
    graph.add_edge(START, CLASSIFY_TICKET)
    graph.add_edge(CLASSIFY_TICKET, RETRIEVE_POLICY)

    # --- Route by sensitivity after policy retrieval ---
    graph.add_conditional_edges(
        RETRIEVE_POLICY,
        route_by_category,
        {
            MINIMAL_CUSTOMER_CONTEXT: MINIMAL_CUSTOMER_CONTEXT,
            CUSTOMER_CONTEXT: CUSTOMER_CONTEXT,
        },
    )

    # Both context paths converge at risk_check
    graph.add_edge(CUSTOMER_CONTEXT, RISK_CHECK)
    graph.add_edge(MINIMAL_CUSTOMER_CONTEXT, RISK_CHECK)

    # --- Core pipeline ---
    graph.add_edge(RISK_CHECK, DRAFT_RESPONSE)
    graph.add_edge(DRAFT_RESPONSE, GROUNDEDNESS_CHECK)

    # --- Groundedness loop with manual review fallback ---
    graph.add_conditional_edges(
        GROUNDEDNESS_CHECK,
        _route_after_groundedness,
        {
            APPROVAL_GATE: APPROVAL_GATE,
            DRAFT_RESPONSE: DRAFT_RESPONSE,
            MANUAL_REVIEW_RESPONSE: MANUAL_REVIEW_RESPONSE,
        },
    )

    # Manual review goes to approval gate
    graph.add_edge(MANUAL_REVIEW_RESPONSE, APPROVAL_GATE)

    # --- Tail: audit → final → end ---
    graph.add_edge(APPROVAL_GATE, AUDIT_LOG)
    graph.add_edge(AUDIT_LOG, FINAL_RESPONSE)
    graph.add_edge(FINAL_RESPONSE, END)

    return graph.compile()


# Module-level singleton
app = build_graph()
