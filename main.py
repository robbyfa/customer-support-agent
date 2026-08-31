"""

Runs 6 demo scenarios through the full LangGraph workflow and
prints the results.

"""

from dotenv import load_dotenv

load_dotenv()

from storage.vector_store import PolicyVectorStore
from tools.registry import configure

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup() -> None:
    """Initialize the vector store and configure the tool registry."""
    vs = PolicyVectorStore(collection_name="copilot_policies")
    count = vs.ingest_policies()
    print(f"✓ Ingested {count} policy chunks into vector store\n")
    configure(vs)


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "name": "Failed Withdrawal",
        "customer_id": "CUST-1001",
        "message": (
            "I tried to withdraw €300 three times and it keeps failing. "
            "Nobody is helping me."
        ),
    },
    {
        "name": "Missing Deposit",
        "customer_id": "CUST-1002",
        "message": (
            "I deposited €100 via bank transfer two hours ago and it still "
            "does not show in my account."
        ),
    },
    {
        "name": "Account Locked",
        "customer_id": "CUST-1003",
        "message": (
            "I keep getting an 'account locked' message when I try to log in. "
            "I did not request this."
        ),
    },
    {
        "name": "Bonus Not Applied",
        "customer_id": "CUST-1004",
        "message": (
            "I signed up with the WELCOME100 promo code but my bonus was "
            "not credited to my account."
        ),
    },
    {
        "name": "Verification Delay",
        "customer_id": "CUST-1005",
        "message": (
            "I submitted my ID and proof of address five days ago and my "
            "account is still not verified. I need to make a withdrawal."
        ),
    },
    {
        "name": "Responsible Gaming - Self-Exclusion",
        "customer_id": "CUST-1006",
        "message": (
            "I want to take a break from gambling. Please help me set a "
            "self-exclusion period."
        ),
    },
]


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render_copilot_response(scenario_name: str, result: dict) -> None:
    """Pretty-print the copilot output to the terminal."""
    fo = result.get("final_output", {})
    classification = fo.get("classification", {})
    risk = fo.get("risk_assessment", {})
    draft = fo.get("draft_response", {})
    recommendation = fo.get("recommendation", {})
    ctx = fo.get("customer_context", {})
    flags = ctx.get("flags", {}) if isinstance(ctx, dict) else {}

    sep = "═" * 70
    thin = "─" * 70

    print(f"\n{sep}")
    print(f"  SCENARIO: {scenario_name}")
    print(sep)

    # Classification
    print("\n  📋 Classification")
    print(f"     Category:      {classification.get('category', '?')}")
    print(f"     Urgency:       {classification.get('urgency', '?')}")
    print(f"     Sentiment:     {classification.get('sentiment', '?')}")
    print(f"     Summary:       {classification.get('summary', '?')}")

    # Customer flags
    if flags:
        print("\n  👤 Customer Flags")
        print(f"     Failed withdrawals:    {flags.get('failed_withdrawal_count', 0)}")
        print(f"     Account locked:        {flags.get('account_locked', False)}")
        print(f"     Verification pending:  {flags.get('verification_pending', False)}")
        print(f"     Responsible gaming:    {flags.get('responsible_gaming_flag', False)}")
        print(f"     Active bonus:          {flags.get('has_active_bonus', False)}")

    # Risk
    print("\n  ⚠️  Risk Assessment")
    print(f"     Risk level:       {risk.get('risk_level', '?')}")
    print(f"     Human review:     {risk.get('requires_human_review', '?')}")
    if risk.get("risk_factors"):
        for factor in risk["risk_factors"]:
            print(f"     • {factor}")

    # Groundedness
    gc = result.get("groundedness_check", {})
    if gc:
        grounded = "✅ Yes" if gc.get("is_grounded") else "❌ No"
        print("\n  🔍 Groundedness Check")
        print(f"     Grounded:    {grounded}")
        print(f"     Confidence:  {gc.get('confidence', '?')}")
        if gc.get("issues"):
            for issue in gc["issues"]:
                print(f"     ⚠ {issue}")

    # Recommendation
    print("\n  💡 Recommendation")
    print(f"     {recommendation.get('recommended_action', 'N/A')[:200]}")

    # Draft response
    print(f"\n  ✉️  Draft Response (tone: {draft.get('tone', '?')})")
    print(thin)
    print(f"  {draft.get('customer_message', 'No draft generated.')}")
    print(thin)

    # Approval
    status = fo.get("status", "?")
    if status == "approved":
        print("\n  ✅ Status: APPROVED - ready to send")
    else:
        print("\n  🔒 Status: PENDING REVIEW - requires human approval")
        if draft.get("reason_approval_required"):
            print(f"     Reason: {draft['reason_approval_required']}")

    # Audit trail
    trail = result.get("audit_trail", [])
    print(f"\n  📝 Audit Trail ({len(trail)} steps)")
    for entry in trail:
        print(f"     → {entry.get('step', '?')} @ {entry.get('timestamp', '?')[:19]}")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run all demo scenarios through the copilot graph."""
    setup()

    from graph.graph import build_graph

    app = build_graph()

    print(f"Running {len(SCENARIOS)} demo scenarios...\n")

    for scenario in SCENARIOS:
        print(f"▶ Running: {scenario['name']}...")

        result = app.invoke(
            {
                "customer_message": scenario["message"],
                "customer_id": scenario["customer_id"],
                "audit_trail": [],
                "draft_retries": 0,
            }
        )

        render_copilot_response(scenario["name"], result)


if __name__ == "__main__":
    main()
