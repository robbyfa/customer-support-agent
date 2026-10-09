# Full workflow evaluation results

Run started: 2026-10-09T07:11:27.011518+00:00. Completed: 2026-10-09T07:16:28.369435+00:00.

Model: `gpt-4o-mini`. Dataset: 25 synthetic cases. This run used live model calls, real policy retrieval, customer context, risk rules, draft generation, dual groundedness checks, retries, and approval gates.

Reviewable cases were scored at their checkpointed interrupt (using an in-memory checkpointer for evaluation) without submitting a human decision. SQLite durability is covered separately by backend integration tests. No messages were sent to customers and no account actions were executed.

## Measured outcomes

| Metric | Result |
|---|---|
| Completed evaluation cases | 25/25 (100.0%) |
| Category classification accuracy | 24/25 (96.0%) |
| Expected policy source in top 3 (cases with a labeled source) | 22/23 (95.7%) |
| Expected-review cases actually interrupted | 9/9 (100.0%) |
| Additional review interrupts vs dataset | 10 |
| Both outputs passed the last LLM groundedness check | 12/25 (48.0%) |
| Safe fallback used after retry exhaustion | 13 |

## Existing evaluator scores

Means below use all attempted cases; execution errors contribute zero. Classification is the mean of category, urgency, and sentiment matches. Sensitivity is the existing risk/sensitivity-flag scorer, which differs from the final interrupt decision. Response and summary scores are literal keyword heuristics, not human judgments of quality. The existing retrieval scorer awards full credit to cases without an expected source; the top-three source metric above excludes those cases.

| Evaluator | Mean |
|---|---|
| Classification fields | 84.0% |
| Policy retrieval scorer | 96.0% |
| Risk/sensitivity flags | 84.0% |
| Draft keyword score | 60.0% |
| Summary keyword score | 84.0% |
| Weighted aggregate | 81.6% |

## Per-case results

Scores are classification / retrieval / sensitivity / draft keywords / summary keywords.

| Case | Expected → actual category | Scores | Aggregate | Review | Fallback |
|---|---|---|---|---|---|
| q01 | withdrawal_issue → withdrawal_issue | 1.00 / 1.00 / 1.00 / 1.00 / 0.00 | 0.850 | Yes | No |
| q02 | withdrawal_issue → withdrawal_issue | 1.00 / 1.00 / 1.00 / 0.00 / 1.00 | 0.800 | Yes | Yes |
| q03 | withdrawal_issue → withdrawal_issue | 0.67 / 1.00 / 1.00 / 0.00 / 1.00 | 0.717 | Yes | Yes |
| q04 | withdrawal_issue → withdrawal_issue | 1.00 / 1.00 / 1.00 / 0.00 / 1.00 | 0.800 | Yes | Yes |
| q05 | withdrawal_issue → withdrawal_issue | 0.67 / 1.00 / 1.00 / 1.00 / 1.00 | 0.917 | Yes | Yes |
| q06 | deposit_issue → deposit_issue | 1.00 / 1.00 / 1.00 / 1.00 / 1.00 | 1.000 | No | No |
| q07 | deposit_issue → deposit_issue | 0.67 / 1.00 / 1.00 / 1.00 / 1.00 | 0.917 | Yes | No |
| q08 | deposit_issue → other | 0.67 / 0.00 / 1.00 / 1.00 / 1.00 | 0.717 | Yes | Yes |
| q09 | deposit_issue → deposit_issue | 0.67 / 1.00 / 0.00 / 0.00 / 0.50 | 0.442 | Yes | Yes |
| q10 | login_issue → login_issue | 0.67 / 1.00 / 0.00 / 1.00 / 1.00 | 0.717 | Yes | No |
| q11 | login_issue → login_issue | 0.67 / 1.00 / 1.00 / 1.00 / 1.00 | 0.917 | No | No |
| q12 | login_issue → login_issue | 1.00 / 1.00 / 1.00 / 1.00 / 0.00 | 0.850 | Yes | No |
| q13 | login_issue → login_issue | 1.00 / 1.00 / 1.00 / 1.00 / 0.00 | 0.850 | Yes | No |
| q14 | bonus_issue → bonus_issue | 1.00 / 1.00 / 1.00 / 0.00 / 1.00 | 0.800 | Yes | Yes |
| q15 | bonus_issue → bonus_issue | 0.67 / 1.00 / 1.00 / 1.00 / 1.00 | 0.917 | No | No |
| q16 | bonus_issue → bonus_issue | 1.00 / 1.00 / 1.00 / 1.00 / 1.00 | 1.000 | No | No |
| q17 | bonus_issue → bonus_issue | 0.67 / 1.00 / 0.00 / 0.00 / 1.00 | 0.517 | Yes | Yes |
| q18 | account_verification → account_verification | 1.00 / 1.00 / 0.00 / 0.00 / 1.00 | 0.600 | Yes | Yes |
| q19 | account_verification → account_verification | 0.67 / 1.00 / 1.00 / 1.00 / 1.00 | 0.917 | No | No |
| q20 | account_verification → account_verification | 0.67 / 1.00 / 1.00 / 0.00 / 1.00 | 0.717 | Yes | Yes |
| q21 | responsible_gaming → responsible_gaming | 0.67 / 1.00 / 1.00 / 0.00 / 1.00 | 0.717 | Yes | Yes |
| q22 | responsible_gaming → responsible_gaming | 1.00 / 1.00 / 1.00 / 0.00 / 1.00 | 0.800 | Yes | Yes |
| q23 | responsible_gaming → responsible_gaming | 1.00 / 1.00 / 1.00 / 1.00 / 0.50 | 0.925 | Yes | No |
| q24 | other → other | 1.00 / 1.00 / 1.00 / 1.00 / 1.00 | 1.000 | Yes | Yes |
| q25 | other → other | 1.00 / 1.00 / 1.00 / 1.00 / 1.00 | 1.000 | No | No |

## Failure cases and limitations

Additional review interrupts: q03, q05, q08, q09, q10, q14, q17, q18, q20, q24.

Safe fallback cases: q02, q03, q04, q05, q08, q09, q14, q17, q18, q20, q21, q22, q24.

Groundedness issue text below is feedback from the LLM judge, not an independently verified finding. Some flags may reflect overly strict judging or missing retrieved context rather than false claims.

- **q01**: summary missing literal keywords: failed, withdrawal
- **q02**: draft missing literal keywords: withdrawal, pending; ungrounded generation replaced with a manual-review template; The response states that the case will be reviewed by the Payments Operations team due to three failed withdrawal attempts, but the policy specifies that cases must be escalated to Payments Operations immediately if there are two or more failed attempts within 48 hours, not just reviewed. The wording implies a delay in escalation which is not supported by the policy.
- **q03**: urgency: expected low, got medium; draft missing literal keywords: withdrawal; ungrounded generation replaced with a manual-review template; The response states that withdrawal requests are processed within 1 to 3 business days, but this timeframe is not mentioned in the provided policy context.; The response implies that a pending deposit affects the ability to withdraw funds, but there is no mention of this in the policy context.; The statement about a withdrawal not being processed until the deposit is confirmed as available in the account is not explicitly supported by the provided policy context. The policy does not mention the need for a deposit to be confirmed before processing a withdrawal.
- **q04**: draft missing literal keywords: reversed, withdrawal; ungrounded generation replaced with a manual-review template; The response states that the matter will be reviewed by the Compliance team, but it does not clarify that the customer's account balance must be restored before any communication is sent, which is a requirement in the policy. Additionally, the response does not provide a clear explanation of the reason for the reversal, which is required by the policy.
- **q05**: urgency: expected low, got medium; ungrounded generation replaced with a manual-review template; The response states that withdrawals must be processed using the same payment method that was used for the deposit, but this is not mentioned in the provided policy context.; The response states that a withdrawal cannot be processed until the deposit is confirmed, but the policy does not explicitly mention this requirement. The policy focuses on failed withdrawals and escalation procedures, not on the status of deposits in relation to withdrawals.
- **q07**: urgency: expected high, got medium
- **q08**: category: expected deposit_issue, got other; expected policy source missing: deposit_policy.md; ungrounded generation replaced with a manual-review template; The response mentions a minimum deposit amount of €10, which is not supported by the provided policy context.
- **q09**: urgency: expected medium, got high; risk/sensitivity flags differ from expected review label; draft missing literal keywords: deposit, declined; summary missing literal keywords: declined; ungrounded generation replaced with a manual-review template; The response suggests escalating to Payments Operations for investigation, which is not mentioned in the policy context. The policy only advises support agents to suggest alternative payment methods if issues persist, without mentioning escalation procedures.
- **q10**: urgency: expected medium, got high; risk/sensitivity flags differ from expected review label
- **q11**: sentiment: expected negative, got neutral
- **q12**: summary missing literal keywords: suspicious, security
- **q13**: summary missing literal keywords: 2FA
- **q14**: draft missing literal keywords: bonus; ungrounded generation replaced with a manual-review template; The response states to check the status of the active welcome bonus, but it does not clarify that only one bonus can be active at a time, which is a critical part of the policy. It implies that the customer can have multiple bonuses active, which is incorrect.
- **q15**: urgency: expected low, got medium
- **q17**: urgency: expected low, got medium; risk/sensitivity flags differ from expected review label; draft missing literal keywords: bonus; ungrounded generation replaced with a manual-review template; The response mentions reviewing 'recent deposits and any applicable promo codes' for the loyalty bonus, but the policy does not specify that promo codes are applicable to loyalty bonuses. The policy only mentions promo codes in the context of bonuses not credited.; The response mentions checking if the bonus was forfeited due to unmet wagering requirements, but the policy does not specify wagering requirements for loyalty bonuses or any other bonuses. It only mentions checking for system errors or active bonuses.
- **q18**: risk/sensitivity flags differ from expected review label; draft missing literal keywords: verification; ungrounded generation replaced with a manual-review template; The response states that the case will be reviewed by the Compliance team, but it does not specify that this escalation is necessary only if the verification is overdue (more than 48 hours) and that the customer should be informed of the expected timeline if documents are found in the queue. The response lacks clarity on whether documents were found or not.
- **q19**: urgency: expected low, got medium
- **q20**: urgency: expected low, got medium; draft missing literal keywords: verification; ungrounded generation replaced with a manual-review template; The statement 'allowing you to play without further issues' is not supported by the policy, as it does not specify what 'play' refers to or that verification directly relates to playing.; The statement that 'it has been five days since submission' is not supported by the policy, which states that documents are reviewed within 24-48 hours. The policy does not specify what to do if the review takes longer than this timeframe.
- **q21**: urgency: expected high, got medium; draft missing literal keywords: self-exclusion; ungrounded generation replaced with a manual-review template; The statement 'Your request will be reviewed by our Responsible Gaming team, who will ensure that it is processed promptly.' is misleading; the policy states that self-exclusion requests must be processed within 1 hour of receipt, not reviewed.
- **q22**: draft missing literal keywords: deposit limit; ungrounded generation replaced with a manual-review template; The response states that the customer has a high risk level and an active responsible gaming flag, but there is no mention in the policy context about how to determine a 'high risk level' or what constitutes an 'active responsible gaming flag'.; The response implies that a mandatory human review is required before any changes to deposit limits can be made, but the policy does not specify that a review is mandatory for all deposit limit changes, only that at-risk behaviour must be flagged for review.
- **q23**: summary missing literal keywords: support
- **q24**: ungrounded generation replaced with a manual-review template; The response does not acknowledge any customer frustration or summarize any issue, which is required for de-escalation according to the policy.; The response does not provide a clear resolution path, which is also required for de-escalation.; The response states 'No action needed - standard inquiry' which does not align with the policy that requires action if a customer is expressing appreciation but there are unresolved issues or complaints. The policy emphasizes de-escalation if the issue can be resolved at the current tier, but it does not support the claim that no action is needed if there are unresolved issues.

### Separation checks

These are heuristic checks of customer/internal response boundaries; inspect the saved outputs before treating a flagged phrase as a real safety failure.

- **q02**: missing_info_quality: missing_information is empty - should list what's still needed
- **q03**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q04**: missing_info_quality: missing_information is empty - should list what's still needed
- **q05**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q08**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q09**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q10**: approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q14**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q15**: recommendation_is_internal: Recommendation lacks action verbs (check, verify, escalate, etc.); missing_info_quality: missing_information is empty - should list what's still needed
- **q17**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q18**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q20**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q21**: missing_info_quality: missing_information is empty - should list what's still needed
- **q22**: missing_info_quality: missing_information is empty - should list what's still needed
- **q23**: missing_info_quality: missing_information is empty - should list what's still needed
- **q24**: missing_info_quality: missing_information is empty - should list what's still needed; approval_correctness: Unexpected human review flag (conservative, not wrong)
- **q25**: recommendation_is_internal: Recommendation lacks action verbs (check, verify, escalate, etc.); missing_info_quality: missing_information is empty - should list what's still needed

This is one run on a small synthetic dataset, not a held-out production benchmark. Groundedness is an LLM judgment, not an independent human assessment. Fallbacks keep drafts flagged by the judge from proceeding but reduce response usefulness. Model sampling and provider updates can change results even with identical inputs.

## Reproduction and artifacts

```bash
uv sync --frozen
# Requires OPENAI_API_KEY in .env; uses configured MODEL_NAME and tracing settings.
uv run python -m evals.run_evals --output docs/full-evaluation-results.json
uv run python -m evals.report
```

- [Per-case scores, generated outputs, and failure diagnostics](full-evaluation-results.json)
- [Run metadata, model settings, dependency versions, and dataset hash](full-evaluation-results.metadata.json)
- [Separate no-LLM retrieval smoke report](retrieval-smoke-results.md)
