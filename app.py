"""Streamlit UI for the Customer Support Resolution Agent.

Usage:
    uv run streamlit run app.py
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("LANGCHAIN_TRACING_V2"):
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

from storage.mock_data import load_customers  # noqa: E402
from storage.vector_store import PolicyVectorStore  # noqa: E402
from tools.registry import configure  # noqa: E402

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Customer Support Copilot",
    page_icon="🎧",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-red    { background: #fee2e2; color: #991b1b; }
    .badge-orange { background: #ffedd5; color: #9a3412; }
    .badge-green  { background: #dcfce7; color: #166534; }
    .badge-blue   { background: #dbeafe; color: #1e40af; }
    .badge-gray   { background: #f3f4f6; color: #374151; }
    .badge-purple { background: #ede9fe; color: #5b21b6; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------

SCENARIOS = {
    "Failed Withdrawal": {
        "customer_id": "CUST-1001",
        "message": "I tried to withdraw €300 three times and it keeps failing. Nobody is helping me.",
    },
    "Missing Deposit": {
        "customer_id": "CUST-1002",
        "message": "I deposited €100 via bank transfer two hours ago and it still does not show in my account.",
    },
    "Account Locked": {
        "customer_id": "CUST-1003",
        "message": "I keep getting an 'account locked' message when I try to log in. I did not request this.",
    },
    "Bonus Not Applied": {
        "customer_id": "CUST-1004",
        "message": "I signed up with the WELCOME100 promo code but my bonus was not credited.",
    },
    "Verification Delay": {
        "customer_id": "CUST-1005",
        "message": "I submitted my ID and proof of address five days ago and my account is still not verified.",
    },
    "Self-Exclusion Request": {
        "customer_id": "CUST-1006",
        "message": "I want to take a break from gambling. Please help me set a self-exclusion period.",
    },
}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def init_session_state():
    defaults = {
        "result": None,
        "customer_id": "CUST-1001",
        "customer_message": "",
        "approved_action": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session_state()

# ---------------------------------------------------------------------------
# Setup (cached)
# ---------------------------------------------------------------------------


@st.cache_resource
def setup_stores():
    vs = PolicyVectorStore(collection_name="copilot_ui")
    vs.ingest_policies()
    configure(vs)
    return vs


@st.cache_resource
def setup_agent():
    setup_stores()
    from graph.graph import build_graph

    return build_graph()


app = setup_agent()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _badge(text: str, color: str) -> str:
    return f'<span class="badge badge-{color}">{text}</span>'


def _urgency_color(u: str) -> str:
    return {"high": "red", "medium": "orange", "low": "green"}.get(u, "gray")


def _sentiment_color(s: str) -> str:
    return {"negative": "red", "neutral": "gray", "positive": "green"}.get(s, "gray")


def _risk_color(r: str) -> str:
    return {"high": "red", "medium": "orange", "low": "green"}.get(r, "gray")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🎧 Support Copilot")
    st.markdown("---")

    # Customer selector
    customers = load_customers()
    customer_options = {c["customer_id"]: f"{c['customer_id']} - {c['name']}" for c in customers}
    selected_id = st.selectbox(
        "Select Customer",
        options=list(customer_options.keys()),
        format_func=lambda x: customer_options[x],
        index=list(customer_options.keys()).index(st.session_state.customer_id),
    )
    st.session_state.customer_id = selected_id

    st.markdown("---")

    # Demo scenario buttons
    st.markdown("**Demo Scenarios**")
    for name, scenario in SCENARIOS.items():
        if st.button(f"▶ {name}", key=f"scenario_{name}", use_container_width=True):
            st.session_state.customer_id = scenario["customer_id"]
            st.session_state.customer_message = scenario["message"]
            st.session_state.result = None
            st.session_state.approved_action = None
            st.rerun()

    st.markdown("---")
    st.markdown("**Suggested Questions**")
    st.caption("• Why is my withdrawal failing?")
    st.caption("• I was charged twice for a deposit")
    st.caption("• I can't access my account")
    st.caption("• Where is my welcome bonus?")
    st.caption("• I need to self-exclude")

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

st.header("Customer Support Resolution Agent")

# Message input
col_input, col_button = st.columns([4, 1])
with col_input:
    message = st.text_area(
        "Customer Message",
        value=st.session_state.customer_message,
        height=100,
        placeholder="Enter the customer message here...",
    )
with col_button:
    st.markdown("<br>", unsafe_allow_html=True)
    run_clicked = st.button("🚀 Run Copilot", type="primary", use_container_width=True)

if run_clicked and message.strip():
    st.session_state.customer_message = message
    st.session_state.approved_action = None

    with st.spinner("Running copilot pipeline..."):
        result = app.invoke(
            {
                "customer_message": message,
                "customer_id": st.session_state.customer_id,
                "audit_trail": [],
                "draft_retries": 0,
            }
        )
        st.session_state.result = result

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

result = st.session_state.result

if result:
    fo = result.get("final_output", {})
    classification = fo.get("classification", {})
    risk = fo.get("risk_assessment", {})
    draft = fo.get("draft_response", {})
    recommendation = fo.get("recommendation", {})
    ctx = fo.get("customer_context", {})
    flags = ctx.get("flags", {}) if isinstance(ctx, dict) else {}
    gc = result.get("groundedness_check", {})

    st.markdown("---")

    # ── 1. Approval status + Recommendation (top priority) ──────────
    if draft.get("approval_required") or risk.get("requires_human_review"):
        st.subheader("🔒 Approval Required")
        if draft.get("reason_approval_required"):
            st.caption(f"Reason: {draft['reason_approval_required']}")

        col_approve, col_reject, _ = st.columns([1, 1, 3])
        with col_approve:
            if st.button("✅ Approve", type="primary", use_container_width=True):
                st.session_state.approved_action = "approved"
                st.rerun()
        with col_reject:
            if st.button("❌ Reject", use_container_width=True):
                st.session_state.approved_action = "rejected"
                st.rerun()

        if st.session_state.approved_action == "approved":
            st.success(
                "✅ **Response approved** - ready to send to customer.\n\n"
                f"*Mock action: message would be sent to "
                f"{fo.get('customer_id', 'unknown')}. "
                f"Ticket status → resolved.*"
            )
        elif st.session_state.approved_action == "rejected":
            st.error(
                "❌ **Response rejected** - draft saved for manual review.\n\n"
                f"*Mock action: case escalated to specialist team for "
                f"{classification.get('category', 'unknown')}. "
                f"Draft preserved in audit trail for reference.*"
            )
    else:
        st.success("✅ Auto-approved - no human review required.")

    # ── 2. Draft response (what to SAY) ────────────────────────────
    st.subheader(f"✉️ Draft Response - tone: {draft.get('tone', '?')}")
    draft_text = draft.get("customer_message", "No draft generated.")
    st.info(draft_text)

    # ── 2b. Internal recommendation (what to DO) ────────────────────
    if recommendation and recommendation.get("recommended_action"):
        st.subheader("🎯 Internal Recommendation")
        action_type = recommendation.get("action_type", "")
        target_team = recommendation.get("target_team", "")
        if action_type or target_team:
            meta_badges = ""
            if action_type:
                meta_badges += _badge(action_type, "purple")
            if target_team:
                meta_badges += _badge(f"→ {target_team}", "blue")
            st.markdown(meta_badges, unsafe_allow_html=True)
        st.warning(recommendation.get("recommended_action", ""))
        if recommendation.get("reason"):
            st.caption(f"**Reason:** {recommendation['reason']}")
        if recommendation.get("missing_information"):
            st.markdown("**Still needed:**")
            for item in recommendation["missing_information"]:
                st.markdown(f"- {item}")

    # ── 3. Classification badges ────────────────────────────────────
    st.subheader("📋 Classification")
    badges_html = (
        _badge(classification.get("category", "?"), "blue")
        + _badge(classification.get("urgency", "?"), _urgency_color(classification.get("urgency", "")))
        + _badge(classification.get("sentiment", "?"), _sentiment_color(classification.get("sentiment", "")))
    )
    st.markdown(badges_html, unsafe_allow_html=True)
    st.caption(classification.get("summary", ""))

    # ── 4. Risk + Groundedness + Policy sources ──────────────────────
    left, right = st.columns(2)

    with left:
        st.subheader("⚠️ Risk Assessment")
        risk_html = (
            _badge(risk.get("risk_level", "?"), _risk_color(risk.get("risk_level", "")))
            + (
                _badge("Human Review", "red")
                if risk.get("requires_human_review")
                else _badge("Auto-OK", "green")
            )
        )
        st.markdown(risk_html, unsafe_allow_html=True)
        for factor in risk.get("risk_factors", []):
            st.markdown(f"- {factor}")

        if gc:
            st.markdown("")
            grounded = gc.get("is_grounded", False)
            conf = gc.get("confidence", 0)
            st.markdown(
                "**Groundedness:** "
                + _badge("Grounded" if grounded else "Not Grounded", "green" if grounded else "red")
                + f" ({conf:.0%} confidence)",
                unsafe_allow_html=True,
            )
            for issue in gc.get("issues", []):
                st.warning(issue)

    with right:
        st.subheader("� Policy Sources")
        trail = result.get("audit_trail", [])
        sources = []
        for entry in trail:
            if entry.get("step") == "retrieve_policy":
                sources = entry.get("sources", [])
                break
        if sources:
            for s in sources:
                name = s.replace("_", " ").replace(".md", "").title()
                st.markdown(f"- 📎 `{s}` - {name}")
        else:
            st.caption("No policies retrieved.")

    # ── 5. Expandable details ───────────────────────────────────────
    st.markdown("---")

    with st.expander(" Customer Context", expanded=False):
        if flags:
            data = {
                "Failed Withdrawals": flags.get("failed_withdrawal_count", 0),
                "Account Locked": "Yes" if flags.get("account_locked") else "No",
                "Verification Pending": "Yes" if flags.get("verification_pending") else "No",
                "Responsible Gaming": "Yes" if flags.get("responsible_gaming_flag") else "No",
                "Active Bonus": "Yes" if flags.get("has_active_bonus") else "No",
                "Risk Level": flags.get("risk_level", "?"),
            }
            for k, v in data.items():
                st.markdown(f"**{k}:** {v}")
        else:
            st.info("No customer context available.")

    with st.expander("📝 Audit Trail", expanded=False):
        trail = result.get("audit_trail", [])
        for entry in trail:
            step = entry.get("step", "?")
            ts = entry.get("timestamp", "?")[:19]
            extras = {k: v for k, v in entry.items() if k not in ("step", "timestamp")}
            extras_str = " | ".join(f"{k}={v}" for k, v in extras.items()) if extras else ""
            st.markdown(f"**{step}** @ `{ts}` {extras_str}")

elif not result and st.session_state.customer_message:
    st.info("Click **Run Copilot** to process the message.")
else:
    st.info("Select a demo scenario from the sidebar or enter a customer message above.")
