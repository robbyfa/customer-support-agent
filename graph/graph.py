"""LangGraph workflow for the Customer Support Resolution Copilot.

Wires all 7 nodes into a linear graph:
  START → classify_ticket → retrieve_policy → customer_context
        → risk_check → draft_response → approval_gate → final_response → END
"""

from langgraph.graph import END, START, StateGraph

from graph.consts import (
    APPROVAL_GATE,
    CLASSIFY_TICKET,
    CUSTOMER_CONTEXT,
    DRAFT_RESPONSE,
    FINAL_RESPONSE,
    RETRIEVE_POLICY,
    RISK_CHECK,
)
from graph.nodes import (
    approval_gate,
    classify_ticket,
    draft_response,
    final_response,
    get_customer_context,
    retrieve_policy,
    risk_check,
)
from graph.state import GraphState


def build_graph() -> StateGraph:
    """Build and compile the support copilot graph."""
    graph = StateGraph(GraphState)

    # --- Add nodes ---
    graph.add_node(CLASSIFY_TICKET, classify_ticket)
    graph.add_node(RETRIEVE_POLICY, retrieve_policy)
    graph.add_node(CUSTOMER_CONTEXT, get_customer_context)
    graph.add_node(RISK_CHECK, risk_check)
    graph.add_node(DRAFT_RESPONSE, draft_response)
    graph.add_node(APPROVAL_GATE, approval_gate)
    graph.add_node(FINAL_RESPONSE, final_response)

    # --- Linear edges ---
    graph.add_edge(START, CLASSIFY_TICKET)
    graph.add_edge(CLASSIFY_TICKET, RETRIEVE_POLICY)
    graph.add_edge(RETRIEVE_POLICY, CUSTOMER_CONTEXT)
    graph.add_edge(CUSTOMER_CONTEXT, RISK_CHECK)
    graph.add_edge(RISK_CHECK, DRAFT_RESPONSE)
    graph.add_edge(DRAFT_RESPONSE, APPROVAL_GATE)
    graph.add_edge(APPROVAL_GATE, FINAL_RESPONSE)
    graph.add_edge(FINAL_RESPONSE, END)

    return graph.compile()


# Module-level singleton - import this for production use.
app = build_graph()
