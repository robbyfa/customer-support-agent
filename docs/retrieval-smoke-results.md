# Evaluation results

Actual local retrieval run. Regenerate with:

```bash
uv sync --frozen
uv run python -m evals.smoke
```

## Scope

This is a component evaluation, not a full LLM workflow benchmark. Each query uses the dataset's expected category (oracle routing), real policy files, and Chroma's default all-MiniLM-L6-v2 embeddings. It measures whether the expected source appears in the top three retrieved chunks. Cases without an expected source are excluded from the denominator. This narrow source-level metric does not assess passage ranking or answer groundedness.

Dataset: 25 cases; 50 policy chunks. Dataset SHA-256: `010613c5db118cbc0dd846d68307a012d51876cccbe38275971f4c6be400e9a8`.

ChromaDB: 1.5.9; ONNX Runtime: 1.29.0.

| Metric | Result |
|---|---|
| Policy source recall@3, oracle category | 23/23 (100.0%) |
| LLM classification | Not measured |
| End-to-end sensitivity detection | Not measured |
| Generated response quality / groundedness | Not measured |

## Cases and failures

| Case | Expected source | Retrieved sources | Result |
|---|---|---|---|
| q01 | withdrawal_policy.md | withdrawal_policy.md | PASS |
| q02 | withdrawal_policy.md | withdrawal_policy.md | PASS |
| q03 | withdrawal_policy.md | withdrawal_policy.md | PASS |
| q04 | withdrawal_policy.md | withdrawal_policy.md | PASS |
| q05 | withdrawal_policy.md | withdrawal_policy.md | PASS |
| q06 | deposit_policy.md | deposit_policy.md | PASS |
| q07 | deposit_policy.md | deposit_policy.md | PASS |
| q08 | deposit_policy.md | deposit_policy.md | PASS |
| q09 | deposit_policy.md | deposit_policy.md | PASS |
| q10 | login_policy.md | login_policy.md | PASS |
| q11 | login_policy.md | login_policy.md | PASS |
| q12 | login_policy.md | login_policy.md | PASS |
| q13 | login_policy.md | login_policy.md | PASS |
| q14 | bonus_policy.md | bonus_policy.md | PASS |
| q15 | bonus_policy.md | bonus_policy.md | PASS |
| q16 | bonus_policy.md | bonus_policy.md | PASS |
| q17 | bonus_policy.md | bonus_policy.md | PASS |
| q18 | account_verification_policy.md | account_verification_policy.md | PASS |
| q19 | account_verification_policy.md | account_verification_policy.md | PASS |
| q20 | account_verification_policy.md | account_verification_policy.md | PASS |
| q21 | responsible_gaming_policy.md | responsible_gaming_policy.md | PASS |
| q22 | responsible_gaming_policy.md | escalation_policy.md, responsible_gaming_policy.md | PASS |
| q23 | responsible_gaming_policy.md | responsible_gaming_policy.md | PASS |
| q24 | — | escalation_policy.md | Unscored |
| q25 | — | escalation_policy.md | Unscored |

Source-recall failures: 0.

Failures above indicate that the expected policy was absent from the top three chunks, even with the correct category supplied. Passing this check does not establish answer correctness.

## Full workflow reproduction

With a configured `OPENAI_API_KEY`, run `uv run python -m evals.run_evals --output docs/full-evaluation-results.json`. Reviewable cases are scored at their interrupt without approving them. See [the full workflow report](evaluation-results.md) for measured model results. No model accuracy figures are inferred from this smoke run.
