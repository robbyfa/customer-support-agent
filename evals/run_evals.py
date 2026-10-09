"""CLI runner for the evaluation framework.

Usage:
    uv run python -m evals.run_evals                  # run all
    uv run python -m evals.run_evals --category withdrawal_issue
    uv run python -m evals.run_evals --question q01
    uv run python -m evals.run_evals --output results.json
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("LANGCHAIN_TRACING_V2"):
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

from evals.dataset import get_by_category, get_dataset
from evals.evaluators import evaluate_response
from evals.separation_evals import evaluate_separation
from storage.vector_store import PolicyVectorStore
from tools.registry import configure


def _score_emoji(score: float) -> str:
    if score >= 0.9:
        return "🟢"
    if score >= 0.7:
        return "🟡"
    if score >= 0.5:
        return "🟠"
    return "🔴"


def _setup():
    vs = PolicyVectorStore(collection_name="eval_policies")
    vs.ingest_policies()
    configure(vs)

    from graph.graph import build_graph

    return build_graph()


def run_eval(
    app,
    cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Run evaluation on a list of cases, return results."""
    results = []

    for case in cases:
        print(f"\n{'─' * 60}")
        print(f"  {case['id']}: {case['customer_message'][:70]}...")
        print(f"  Expected: {case['expected_category']} | review={case['expected_human_review']}")

        try:
            output = app.invoke(
                {
                    "customer_message": case["customer_message"],
                    "customer_id": case["customer_id"],
                    "audit_trail": [],
                    "draft_retries": 0,
                },
                {"configurable": {"thread_id": str(uuid4())}},
            )
            if not output.get("final_output"):
                output["final_output"] = {key: output.get(key, {}) for key in (
                    "classification", "risk_assessment", "draft_response", "recommendation",
                )}
            scores = evaluate_response(case, output)

            actual_cat = output.get("final_output", {}).get("classification", {}).get("category", "?")
            emoji = _score_emoji(scores["aggregate"])

            print(f"  Actual:   {actual_cat}")
            print(
                f"  Scores:   "
                f"class={scores['classification']:.2f} "
                f"retr={scores['retrieval']:.2f} "
                f"sens={scores['sensitivity']:.2f} "
                f"resp={scores['response_quality']:.2f} "
                f"kw={scores['keywords']:.2f}"
            )
            print(f"  {emoji} Aggregate: {scores['aggregate']:.3f}")

            results.append({
                "id": case["id"],
                "expected_category": case["expected_category"],
                "actual_category": actual_cat,
                "scores": scores,
                "separation": evaluate_separation(case, output),
                "observed": {
                    "classification": output.get("classification"),
                    "risk_assessment": output.get("risk_assessment"),
                    "draft_response": output.get("draft_response"),
                    "recommendation": output.get("recommendation"),
                    "groundedness_check": output.get("groundedness_check"),
                    "draft_retries": output.get("draft_retries", 0),
                    "pending_review": bool(output.get("__interrupt__")),
                    "safe_fallback": any(e.get("step") == "manual_review_response"
                                         for e in output.get("audit_trail", [])),
                    "policy_sources": sorted({source for e in output.get("audit_trail", [])
                                              if e.get("step") == "retrieve_policy"
                                              for source in e.get("sources", [])}),
                },
                "status": "ok",
            })

        except Exception as e:
            error = type(e).__name__
            print(f"  🔴 ERROR: {error}")
            results.append({
                "id": case["id"],
                "expected_category": case["expected_category"],
                "actual_category": "error",
                "scores": {"aggregate": 0.0},
                "status": "error",
                "error": error,
            })

    return results


def print_summary(results: list[dict[str, Any]]) -> None:
    """Print a summary table of evaluation results."""
    print(f"\n{'═' * 60}")
    print("  EVALUATION SUMMARY")
    print(f"{'═' * 60}")

    total = len(results)
    ok = [r for r in results if r["status"] == "ok"]
    errors = total - len(ok)

    if ok:
        agg_scores = [r["scores"]["aggregate"] for r in ok]
        avg = sum(agg_scores) / len(agg_scores)
        min_score = min(agg_scores)
        max_score = max(agg_scores)

        print(f"\n  Cases run:      {total}")
        print(f"  Errors:         {errors}")
        print(f"  Avg aggregate:  {avg:.3f} {_score_emoji(avg)}")
        print(f"  Min:            {min_score:.3f} {_score_emoji(min_score)}")
        print(f"  Max:            {max_score:.3f} {_score_emoji(max_score)}")

        # Per-dimension averages
        dims = ["classification", "retrieval", "sensitivity", "response_quality", "keywords"]
        print(f"\n  {'Dimension':<20} {'Avg':>6}")
        print(f"  {'─' * 28}")
        for dim in dims:
            dim_scores = [r["scores"].get(dim, 0) for r in ok]
            dim_avg = sum(dim_scores) / len(dim_scores) if dim_scores else 0
            print(f"  {dim:<20} {dim_avg:>6.3f} {_score_emoji(dim_avg)}")

        # Per-category breakdown
        categories = sorted({r["expected_category"] for r in ok})
        print(f"\n  {'Category':<25} {'Count':>5} {'Avg':>6}")
        print(f"  {'─' * 38}")
        for cat in categories:
            cat_results = [r for r in ok if r["expected_category"] == cat]
            cat_avg = sum(r["scores"]["aggregate"] for r in cat_results) / len(cat_results)
            print(f"  {cat:<25} {len(cat_results):>5} {cat_avg:>6.3f} {_score_emoji(cat_avg)}")
    else:
        print(f"\n  No successful evaluations. {errors} errors.")

    print(f"\n{'═' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Run evaluation suite")
    parser.add_argument("--category", type=str, help="Filter by expected category")
    parser.add_argument("--question", type=str, help="Run a single question by ID")
    parser.add_argument("--output", type=str, help="Save results to JSON file")
    args = parser.parse_args()

    app = _setup()

    if args.question:
        cases = [c for c in get_dataset() if c["id"] == args.question]
        if not cases:
            print(f"Question {args.question} not found.")
            sys.exit(1)
    elif args.category:
        cases = get_by_category(args.category)
        if not cases:
            print(f"No cases for category {args.category}.")
            sys.exit(1)
    else:
        cases = get_dataset()

    print(f"Running {len(cases)} evaluation case(s)...")
    started_at = datetime.now(UTC).isoformat()
    results = run_eval(app, cases)
    print_summary(results)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        metadata = {
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "model": os.getenv("MODEL_NAME", "gpt-4o-mini"),
            "temperatures": {"classification": 0, "draft": 0.3, "recommendation": 0, "groundedness": 0},
            "dataset_sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
            "case_count": len(cases),
            "packages": {name: importlib.metadata.version(name) for name in
                         ("langgraph", "langchain-openai", "chromadb", "onnxruntime")},
            "review_mode": "Score suspended drafts; never resume or approve cases",
        }
        Path(args.output).with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"\nResults saved to {args.output}")
    if any(r["status"] == "error" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
