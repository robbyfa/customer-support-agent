"""Policy-related LangChain tools.

Read-only tool for searching the policy vector store via RAG.
Requires ``tools.registry.configure()`` to be called first.
"""

from langchain_core.tools import tool

from tools.registry import get_vector_store


@tool
def search_policy_documents(query: str, n_results: int = 3) -> dict:
    """Search internal policy documents for guidance relevant to a support case.

    Returns the top matching policy chunks with source file names and
    relevance scores. Use this to ground responses in official policy.
    """
    store = get_vector_store()
    results = store.search(query, n_results=n_results)
    return {
        "query": query,
        "total_results": len(results),
        "results": results,
    }
