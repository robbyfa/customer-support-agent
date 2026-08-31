"""Policy vector store for RAG retrieval using ChromaDB.

Ingests markdown policy documents by section (heading-aware chunking),
stores category metadata for filtered retrieval, and provides semantic search.
"""

import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.config import Settings

_DEFAULT_POLICIES_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"

# Map policy filenames to classification categories for metadata filtering.
_SOURCE_TO_CATEGORY: dict[str, list[str]] = {
    "withdrawal_policy.md": ["withdrawal_issue"],
    "deposit_policy.md": ["deposit_issue"],
    "bonus_policy.md": ["bonus_issue"],
    "login_policy.md": ["login_issue"],
    "account_verification_policy.md": ["account_verification"],
    "responsible_gaming_policy.md": ["responsible_gaming"],
    "escalation_policy.md": [
        "withdrawal_issue",
        "deposit_issue",
        "login_issue",
        "bonus_issue",
        "account_verification",
        "responsible_gaming",
        "other",
    ],
}


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
    ) -> int:
        """Read all .md files, split by markdown sections, and upsert.

        Each chunk corresponds to a complete markdown section (heading +
        its body) so content is never cut mid-sentence.

        Returns the number of chunks ingested.
        """
        policies_dir = Path(policies_dir) if policies_dir else _DEFAULT_POLICIES_DIR

        documents: list[str] = []
        metadatas: list[dict] = []
        ids: list[str] = []

        for md_file in sorted(policies_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            sections = self._split_by_sections(text)
            categories = _SOURCE_TO_CATEGORY.get(md_file.name, ["other"])
            # ChromaDB metadata values must be str/int/float/bool
            category_str = ",".join(categories)

            for idx, (heading, body) in enumerate(sections):
                # Prefix chunk with source and section for context
                chunk = f"Source: {md_file.name}\nSection: {heading}\n\n{body}"
                doc_id = self._make_id(md_file.name, idx)

                documents.append(chunk)
                metadatas.append(
                    {
                        "source": md_file.name,
                        "section": heading,
                        "chunk_index": idx,
                        "categories": category_str,
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
        category: str | None = None,
    ) -> list[dict]:
        """Return the top-*n_results* chunks matching *query*.

        If *category* is provided, results are filtered to chunks from
        policies mapped to that category. Falls back to unfiltered search
        if the filtered search returns no results.

        Each result dict contains: content, source, section, chunk_index, score.
        """
        where_filter = None
        if category:
            where_filter = {"categories": {"$contains": category}}

        results = self._collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
        )

        output = self._parse_results(results)

        # Fallback: if category filter returned nothing, try unfiltered
        if not output and category:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
            )
            output = self._parse_results(results)

        return output

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Delete the collection and recreate it (empty)."""
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _split_by_sections(text: str) -> list[tuple[str, str]]:
        """Split markdown text into (heading, body) pairs.

        Splits on ## headings. The document title (# heading) becomes
        the first section. Sections without a heading get "Introduction".
        """
        # Split on lines that start with ## (but not ### which is a sub-section)
        # We keep all heading levels to get granular sections.
        pattern = r"^(#{1,3})\s+(.+)$"
        sections: list[tuple[str, str]] = []
        current_heading = "Introduction"
        current_lines: list[str] = []

        for line in text.split("\n"):
            match = re.match(pattern, line)
            if match:
                # Save previous section
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append((current_heading, body))
                current_heading = match.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Save the last section
        body = "\n".join(current_lines).strip()
        if body:
            sections.append((current_heading, body))

        return sections

    @staticmethod
    def _parse_results(results: dict) -> list[dict]:
        """Convert ChromaDB query results to a list of dicts."""
        output: list[dict] = []
        if not results["documents"] or not results["documents"][0]:
            return output

        for doc, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append(
                {
                    "content": doc,
                    "source": meta["source"],
                    "section": meta.get("section", ""),
                    "chunk_index": meta["chunk_index"],
                    "score": 1 - distance,
                }
            )

        return output

    @staticmethod
    def _make_id(filename: str, chunk_index: int) -> str:
        """Deterministic ID so upserts are idempotent."""
        raw = f"{filename}::{chunk_index}"
        return hashlib.md5(raw.encode()).hexdigest()
