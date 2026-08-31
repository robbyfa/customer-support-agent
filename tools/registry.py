"""Tool registry - central configuration for shared resources.

Call ``configure()`` once at startup (e.g. in ``main.py`` or ``app.py``)
before any tool that depends on the vector store is invoked.
"""

from storage.vector_store import PolicyVectorStore

_vector_store: PolicyVectorStore | None = None


def configure(vector_store: PolicyVectorStore) -> None:
    """Register the *vector_store* instance for use by policy tools."""
    global _vector_store
    _vector_store = vector_store


def get_vector_store() -> PolicyVectorStore:
    """Return the configured vector store, or raise if not yet configured."""
    if _vector_store is None:
        raise RuntimeError(
            "Vector store not configured. Call tools.registry.configure() "
            "with a PolicyVectorStore instance before using policy tools."
        )
    return _vector_store
