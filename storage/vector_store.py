"""Policy vector store for RAG retrieval using ChromaDB.

Ingests markdown policy documents, chunks them, and provides
semantic search over the policy corpus.
"""

import hashlib
from pathlib import Path

import chromadb
from chromadb.config import Settings


_DEFAULT_POLICIES_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"


class PolicyVectorStore:
    """ChromaDB-backed vector store for policy documents.

    Uses ChromaDB's default embedding function (all-MiniLM-L6-v2 via
    onnxruntime) so no external API key is needed.
    """

    def __init__(
        self,
        collection_name: str = "policies",
        persist_directory: str | None = None,
    ) -> None:
        if persist_directory:
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
        else:
            self._client = chromadb.EphemeralClient(
                settings=Settings(anonymized_telemetry=False),
            )

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_policies(
        self,
        policies_dir: Path | str | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> int:
        """Read all .md files from *policies_dir*, chunk them, and upsert.

        Returns the number of chunks ingested.
        """
        policies_dir = Path(policies_dir) if policies_dir else _DEFAULT_POLICIES_DIR

        documents: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []

        for md_file in sorted(policies_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            chunks = self._split_text(text, chunk_size, chunk_overlap)

            for idx, chunk in enumerate(chunks):
                doc_id = self._make_id(md_file.name, idx)
                documents.append(chunk)
                metadatas.append(
                    {
                        "source": md_file.name,
                        "chunk_index": idx,
                    }
                )
                ids.append(doc_id)

        if documents:
            self._collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )

        return len(documents)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 3,
    ) -> list[dict]:
        """Return the top-*n_results* chunks matching *query*.

        Each result dict contains: content, source, chunk_index, score.
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        output: list[dict] = []
        # results is a dict with parallel lists keyed by the batch index
        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append(
                {
                    "content": doc,
                    "source": meta["source"],
                    "chunk_index": meta["chunk_index"],
                    "score": 1 - distance,  # cosine distance → similarity
                }
            )

        return output

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Delete the collection and recreate it (empty)."""
        self._client.delete_collection(self._collection.name)
        self._collection = self._client.get_or_create_collection(
            name="policies",
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _split_text(
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[str]:
        """Split *text* into overlapping chunks by character count."""
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - chunk_overlap
        return chunks

    @staticmethod
    def _make_id(filename: str, chunk_index: int) -> str:
        """Deterministic ID so upserts are idempotent."""
        raw = f"{filename}::{chunk_index}"
        return hashlib.md5(raw.encode()).hexdigest()
