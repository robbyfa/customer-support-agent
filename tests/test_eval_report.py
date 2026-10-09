"""The report must not inflate scores by dropping errors or unlabeled cases."""

from evals.report import render_report


def test_errors_count_against_outcomes_but_unlabeled_sources_are_excluded():
    cases = [
        {"id": "q1", "expected_category": "other", "expected_policy_source": None, "expected_human_review": False},
        {"id": "q2", "expected_category": "deposit_issue", "expected_policy_source": "deposit_policy.md",
         "expected_human_review": True},
    ]
    results = [{
        "id": case["id"], "status": "error", "error": "AuthenticationError", "actual_category": "error",
        "expected_category": case["expected_category"], "scores": {"aggregate": 0},
    } for case in cases]
    report = render_report(results, {"started_at": "start", "finished_at": "end", "model": "test"}, cases)
    assert "Category classification accuracy | 0/2 (0.0%)" in report
    assert "labeled source) | 0/1 (0.0%)" in report
    assert "Expected-review cases actually interrupted | 0/1 (0.0%)" in report
    assert "**q1**: Execution error: AuthenticationError" in report
    assert "**q2**: Execution error: AuthenticationError" in report


def test_empty_run_is_not_reported_as_perfect():
    report = render_report([], {"started_at": "start", "finished_at": "end", "model": "test"}, [])
    assert "Completed evaluation cases | Not measured" in report
    assert "Weighted aggregate | 0.0%" in report


def test_runner_scores_interrupt_without_resuming():
    from evals.dataset import get_dataset
    from evals.run_evals import run_eval

    class InterruptedGraph:
        def __init__(self):
            self.calls = 0

        def invoke(self, state, config):
            self.calls += 1
            assert config["configurable"]["thread_id"]
            return {
                "__interrupt__": (object(),),
                "classification": {"category": "withdrawal_issue", "urgency": "high", "sentiment": "negative"},
                "draft_response": {"customer_message": "Your withdrawal needs review.", "approval_required": True},
                "risk_assessment": {"requires_human_review": True},
                "recommendation": {},
                "audit_trail": [{"step": "retrieve_policy", "sources": ["withdrawal_policy.md"]}],
            }

    graph = InterruptedGraph()
    result = run_eval(graph, get_dataset()[:1])[0]
    assert graph.calls == 1
    assert result["status"] == "ok"
    assert result["observed"]["pending_review"] is True
    assert result["scores"]["classification"] == 1.0
    assert result["observed"]["policy_sources"] == ["withdrawal_policy.md"]


def test_runner_does_not_save_provider_error_details():
    from evals.dataset import get_dataset
    from evals.run_evals import run_eval

    class FailedGraph:
        def invoke(self, *args):
            raise RuntimeError("sensitive provider message")

    result = run_eval(FailedGraph(), get_dataset()[:1])[0]
    assert result["status"] == "error"
    assert result["error"] == "RuntimeError"
    assert "sensitive provider message" not in str(result)
