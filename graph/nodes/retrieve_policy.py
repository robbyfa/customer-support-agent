"""Node: retrieve_policy - retrieves relevant policy documents from the
vector store based on the ticket classification, with category filtering.
"""

from datetime import UTC, datetime
from typing import Any

from graph.state import GraphState
from tools.registry import get_vector_store


def retrieve_policy(state: GraphState) -> dict[str, Any]:
    """Retrieve policy documents relevant to the classified issue.

    Uses category metadata filtering for precise retrieval, with
    automatic fallback to unfiltered search if no results are found.
    """
    classification = state.get("classification", {})
    category = classification.get("category", "other")
    summary = classification.get("summary", "")

    query = f"{category} {summary}".strip() or "support policy"

    store = get_vector_store()
    results = store.search(query, n_results=3, category=category)

    policy_context = [r["content"] for r in results]
    sources = list({r["source"] for r in results})

    audit_entry = {
        "step": "retrieve_policy",
        "timestamp": datetime.now(UTC).isoformat(),
        "query": query,
        "category_filter": category,
        "sources": sources,
        "chunks_retrieved": len(results),
    }

    return {
        "policy_context": policy_context,
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
