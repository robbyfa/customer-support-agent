"""Reproducible, no-LLM policy retrieval evaluation with oracle categories."""

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

from evals.dataset import get_dataset
from storage.vector_store import PolicyVectorStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/retrieval-smoke-results.md")
    args = parser.parse_args()
    cases = get_dataset()
    store = PolicyVectorStore(collection_name="evaluation_smoke")
    chunks = store.ingest_policies()
    rows = []
    for case in cases:
        hits = store.search(case["customer_message"], category=case["expected_category"])
        sources = sorted({hit["source"] for hit in hits})
        expected = case["expected_policy_source"]
        rows.append((case["id"], expected, sources, expected in sources if expected else None))
    scored = [row for row in rows if row[3] is not None]
    passed = sum(row[3] for row in scored)
    digest = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()
    lines = [
        "# Evaluation results", "",
        "Actual local retrieval run. Regenerate with:", "",
        "```bash", "uv sync --frozen", "uv run python -m evals.smoke", "```", "",
        "## Scope", "",
        "This is a component evaluation, not a full LLM workflow benchmark. Each query uses the dataset's "
        "expected category (oracle routing), real policy files, and Chroma's default all-MiniLM-L6-v2 embeddings. "
        "It measures whether the expected source appears in the top three retrieved chunks. "
        "Cases without an expected source are excluded from the denominator. "
        "This narrow source-level metric does not assess passage ranking or answer groundedness.", "",
        f"Dataset: {len(cases)} cases; {chunks} policy chunks. Dataset SHA-256: `{digest}`.", "",
        f"ChromaDB: {importlib.metadata.version('chromadb')}; "
        f"ONNX Runtime: {importlib.metadata.version('onnxruntime')}.", "",
        "| Metric | Result |", "|---|---|",
        f"| Policy source recall@3, oracle category | {passed}/{len(scored)} ({passed / len(scored):.1%}) |",
        "| LLM classification | Not measured |", "| End-to-end sensitivity detection | Not measured |",
        "| Generated response quality / groundedness | Not measured |", "",
        "## Cases and failures", "",
        "| Case | Expected source | Retrieved sources | Result |", "|---|---|---|---|",
    ]
    for case_id, expected, sources, ok in rows:
        verdict = "PASS" if ok else "FAIL" if ok is False else "Unscored"
        lines.append(f"| {case_id} | {expected or '—'} | {', '.join(sources)} | {verdict} |")
    lines += ["", f"Source-recall failures: {len(scored) - passed}.", "", "Failures above indicate that the expected policy was absent from the top three chunks, "
              "even with the correct category supplied. Passing this check does not establish answer correctness.", "",
              "## Full workflow reproduction", "",
              "With a configured `OPENAI_API_KEY`, run "
              "`uv run python -m evals.run_evals --output docs/full-evaluation-results.json`. "
              "Reviewable cases are scored at their interrupt without approving them. "
              "See [the full workflow report](evaluation-results.md) for measured model results. "
              "No model accuracy figures are inferred from this smoke run.", ""]
    Path(args.output).write_text("\n".join(lines))
    print(f"Policy retrieval: {passed}/{len(scored)}. Report: {args.output}")
    # A modest floor catches major retrieval regressions, while the artifact lists every miss.
    if passed / len(scored) < 0.8:
        raise SystemExit("Policy recall@3 below the 80% smoke threshold")


if __name__ == "__main__":
    main()
