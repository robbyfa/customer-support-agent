"""Render a measured full-workflow report from saved results; makes no API calls."""

import argparse
import json
from pathlib import Path

from evals.dataset import get_dataset


def ratio(numerator, denominator):
    return f"{numerator}/{denominator} ({numerator / denominator:.1%})" if denominator else "Not measured"


def render_report(results, metadata, dataset):
    expected = {case["id"]: case for case in dataset}
    successful = [r for r in results if r["status"] == "ok"]
    total = len(results)
    source_cases = [r for r in results if expected[r["id"]]["expected_policy_source"]]
    required = [r for r in results if expected[r["id"]]["expected_human_review"]]
    category_correct = sum(r.get("actual_category") == expected[r["id"]]["expected_category"] for r in results)
    source_correct = sum(
        expected[r["id"]]["expected_policy_source"] in r.get("observed", {}).get("policy_sources", [])
        for r in source_cases
    )
    review_caught = sum(r.get("observed", {}).get("pending_review", False) for r in required)
    unnecessary = [r["id"] for r in successful if r["observed"]["pending_review"]
                   and not expected[r["id"]]["expected_human_review"]]
    fallbacks = [r["id"] for r in successful if r["observed"]["safe_fallback"]]
    grounded = sum(bool(r["observed"].get("groundedness_check", {}).get("is_grounded")) for r in successful)
    lines = [
        "# Full workflow evaluation results", "",
        f"Run started: {metadata['started_at']}. Completed: {metadata['finished_at']}.", "",
        f"Model: `{metadata['model']}`. Dataset: {total} synthetic cases. "
        "This run used live model calls, real policy retrieval, customer context, risk rules, "
        "draft generation, dual groundedness checks, retries, and approval gates.", "",
        "Reviewable cases were scored at their checkpointed interrupt (using an in-memory checkpointer for evaluation) "
        "without submitting a human decision. "
        "SQLite durability is covered separately by backend integration tests. "
        "No messages were sent to customers and no account actions were executed.", "",
        "## Measured outcomes", "",
        "| Metric | Result |", "|---|---|",
        f"| Completed evaluation cases | {ratio(len(successful), total)} |",
        f"| Category classification accuracy | {ratio(category_correct, total)} |",
        f"| Expected policy source in top 3 (cases with a labeled source) | {ratio(source_correct, len(source_cases))} |",
        f"| Expected-review cases actually interrupted | {ratio(review_caught, len(required))} |",
        f"| Additional review interrupts vs dataset | {len(unnecessary)} |",
        f"| Both outputs passed the last LLM groundedness check | {ratio(grounded, total)} |",
        f"| Safe fallback used after retry exhaustion | {len(fallbacks)} |", "",
        "## Existing evaluator scores", "",
        "Means below use all attempted cases; execution errors contribute zero. "
        "Classification is the mean of category, urgency, and sentiment matches. "
        "Sensitivity is the existing risk/sensitivity-flag scorer, which differs from the final interrupt decision. "
        "Response and summary scores are literal keyword heuristics, not human judgments of quality. "
        "The existing retrieval scorer awards full credit to cases without an expected source; "
        "the top-three source metric above excludes those cases.", "",
        "| Evaluator | Mean |", "|---|---|",
    ]
    for key, label in (
        ("classification", "Classification fields"), ("retrieval", "Policy retrieval scorer"),
        ("sensitivity", "Risk/sensitivity flags"), ("response_quality", "Draft keyword score"),
        ("keywords", "Summary keyword score"), ("aggregate", "Weighted aggregate"),
    ):
        mean = sum(r["scores"].get(key, 0) for r in results) / total if total else 0
        lines.append(f"| {label} | {mean:.1%} |")
    lines += ["", "## Per-case results", "",
              "Scores are classification / retrieval / sensitivity / draft keywords / summary keywords.", "",
              "| Case | Expected → actual category | Scores | Aggregate | Review | Fallback |",
              "|---|---|---|---|---|---|"]
    for result in results:
        observed = result.get("observed", {})
        scores = result["scores"]
        dims = " / ".join(f"{scores.get(key, 0):.2f}" for key in (
            "classification", "retrieval", "sensitivity", "response_quality", "keywords"))
        lines.append(
            f"| {result['id']} | {result['expected_category']} → {result['actual_category']} | {dims} | "
            f"{scores['aggregate']:.3f} | {'Yes' if observed.get('pending_review') else 'No'} | "
            f"{'Yes' if observed.get('safe_fallback') else 'No'} |"
        )
    lines += ["", "## Failure cases and limitations", "",
              f"Additional review interrupts: {', '.join(unnecessary) or 'none'}.", "",
              f"Safe fallback cases: {', '.join(fallbacks) or 'none'}.", "",
              "Groundedness issue text below is feedback from the LLM judge, not an independently verified finding. "
              "Some flags may reflect overly strict judging or missing retrieved context rather than false claims.", ""]
    for result in results:
        case = expected[result["id"]]
        observations = result.get("observed", {})
        issues = []
        if result["status"] != "ok":
            issues.append(f"Execution error: {result.get('error', 'unknown')}")
        else:
            classification = observations["classification"]
            for field in ("category", "urgency", "sentiment"):
                if classification.get(field) != case.get(f"expected_{field}"):
                    issues.append(f"{field}: expected {case.get(f'expected_{field}')}, got {classification.get(field)}")
            if result["scores"]["sensitivity"] < 1:
                issues.append("risk/sensitivity flags differ from expected review label")
            draft = observations["draft_response"].get("customer_message", "").lower()
            missing = [word for word in case["must_include"] if word.lower() not in draft]
            forbidden = [word for word in case["must_not_include"] if word.lower() in draft]
            if missing:
                issues.append(f"draft missing literal keywords: {', '.join(missing)}")
            if forbidden:
                issues.append(f"draft contains prohibited substrings: {', '.join(forbidden)}")
            summary = classification.get("summary", "").lower()
            missing_summary = [word for word in case["must_include"] if word.lower() not in summary]
            if missing_summary:
                issues.append(f"summary missing literal keywords: {', '.join(missing_summary)}")
            source = case["expected_policy_source"]
            if source and source not in observations["policy_sources"]:
                issues.append(f"expected policy source missing: {source}")
            if observations["safe_fallback"]:
                issues.append("ungrounded generation replaced with a manual-review template")
                issues.extend(observations.get("groundedness_check", {}).get("issues", []))
        if issues:
            lines.append(f"- **{result['id']}**: " + "; ".join(issues).replace("\n", " "))
    lines += ["", "### Separation checks", "",
              "These are heuristic checks of customer/internal response boundaries; inspect the saved outputs "
              "before treating a flagged phrase as a real safety failure.", ""]
    for result in successful:
        failures = [f"{name}: {', '.join(check['issues'])}" for name, check in result["separation"]["checks"].items()
                    if check.get("issues")]
        if failures:
            lines.append(f"- **{result['id']}**: " + "; ".join(failures))
    lines += ["", "This is one run on a small synthetic dataset, not a held-out production benchmark. "
              "Groundedness is an LLM judgment, not an independent human assessment. "
              "Fallbacks keep drafts flagged by the judge from proceeding but reduce response usefulness. "
              "Model sampling and provider updates can change results even with identical inputs.", "",
              "## Reproduction and artifacts", "",
              "```bash", "uv sync --frozen",
              "# Requires OPENAI_API_KEY in .env; uses configured MODEL_NAME and tracing settings.",
              "uv run python -m evals.run_evals --output docs/full-evaluation-results.json",
              "uv run python -m evals.report", "```", "",
              "- [Per-case scores, generated outputs, and failure diagnostics](full-evaluation-results.json)",
              "- [Run metadata, model settings, dependency versions, and dataset hash](full-evaluation-results.metadata.json)",
              "- [Separate no-LLM retrieval smoke report](retrieval-smoke-results.md)", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="docs/full-evaluation-results.json")
    parser.add_argument("--output", default="docs/evaluation-results.md")
    args = parser.parse_args()
    path = Path(args.input)
    results = json.loads(path.read_text())
    metadata = json.loads(path.with_suffix(".metadata.json").read_text())
    Path(args.output).write_text(render_report(results, metadata, get_dataset()))
    print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
