# Customer Support Resolution Copilot — Project Spec

## 1. Project Overview

**Customer Support Resolution Copilot** is an applied GenAI assistant for support agents. It helps classify customer messages, retrieve relevant policy guidance, inspect mock customer/account data, draft responses, flag sensitive cases, and require human approval before any customer-facing action.

The goal is to show that you can build a **business-facing AI Engineer project** using LangChain, LangGraph, RAG, structured outputs, tool calling, evaluation, and human-in-the-loop workflows.

This should not be a generic chatbot. It should behave like an internal support workflow assistant.

---

## 2. One-line CV Description

> Built a customer support AI copilot using LangGraph, LangChain and RAG to classify support cases, retrieve policy guidance, call customer/ticket tools, draft grounded responses, flag sensitive issues and enforce human approval before customer-facing actions.

---

## 3. Core Use Case

A support agent receives a customer message:

```text
I tried to withdraw €300 three times and it keeps failing. Nobody is helping me.
```

The copilot should return:

```text
Category: withdrawal_issue
Urgency: high
Sentiment: negative
Sensitive case: yes
Human review required: true

Relevant policy:
- withdrawal_policy.md

Customer context:
- Customer has 3 failed withdrawals in the last 24 hours
- Account is verified
- No active payment block found

Suggested internal action:
- Escalate to Payments Operations
- Do not tell the customer the issue is resolved until payment status is confirmed

Draft response:
...
```

---

## 4. MVP Scope

The MVP should support 5–6 customer issue types:

```text
withdrawal_issue
deposit_issue
login_issue
bonus_issue
account_verification
responsible_gaming
```

The system should:

1. Accept a customer message.
2. Classify the issue using structured output.
3. Retrieve relevant policy documents using RAG.
4. Call mock tools for customer/account/ticket context.
5. Generate a suggested support response.
6. Flag sensitive or high-risk cases.
7. Require human approval before “sending” the response.
8. Log trace/evaluation metadata.

---

## 5. Main Differentiator

Most support AI projects are just:

```text
customer message → chatbot reply
```

This project should be:

```text
customer message
→ structured classification
→ policy retrieval
→ tool-based customer context
→ risk/sensitivity check
→ response drafting
→ approval gate
→ audit log
```

That is what makes it a real AI Engineer portfolio project.

---

## 6. Suggested Tech Stack

```text
Python
uv for dependency and virtual environment management
FastAPI
Streamlit
LangChain
LangGraph
LangSmith
Pydantic
Chroma
SQLite
Docker
pytest
```

LLM provider:

```text
OpenAI or Gemini
```

Keep it provider-configurable if possible:

```env
MODEL_PROVIDER=openai
MODEL_NAME=gpt-4o-mini
```

or:

```env
MODEL_PROVIDER=gemini
MODEL_NAME=gemini-...
```

---

## 6.1 Dependency Management with uv

Use **uv** for dependency management and local development. The repository should include a `pyproject.toml` file and, once dependencies are locked, a `uv.lock` file.

Recommended setup commands:

```bash
# Create the project environment
uv venv

# Install dependencies from pyproject.toml / uv.lock
uv sync

# Add new dependencies
uv add langchain langgraph langchain-openai langchain-google-genai langsmith pydantic chromadb streamlit fastapi uvicorn pytest python-dotenv

# Add development dependencies
uv add --dev ruff pytest pytest-cov
```

Run commands through uv:

```bash
uv run streamlit run app.py
uv run python main.py
uv run pytest -v
uv run python -m evals.run_evals
```

The README should avoid `pip install -r requirements.txt` as the main setup path. Use `uv sync` as the primary installation method.

---

## 7. Architecture

```text
Support Agent UI
      │
      ▼
Customer message
      │
      ▼
LangGraph workflow
      │
      ├── classify_ticket
      ├── retrieve_policy_context
      ├── get_customer_context
      ├── get_ticket_history
      ├── risk_check
      ├── draft_response
      ├── approval_gate
      └── final_response
      │
      ▼
Audit log + LangSmith trace
```

---

## 8. LangGraph Workflow

### Main graph

```text
START
  ↓
classify_ticket
  ↓
route_by_category
  ↓
retrieve_policy_context
  ↓
get_customer_context
  ↓
risk_check
  ↓
draft_response
  ↓
approval_gate
  ↓
final_response
  ↓
END
```

### Conditional routing

```text
withdrawal_issue       → payments workflow
deposit_issue          → payments workflow
bonus_issue            → bonus policy workflow
login_issue            → account access workflow
account_verification   → verification workflow
responsible_gaming     → sensitive case workflow
```

### Sensitive cases

Responsible gaming, repeated failed withdrawals, account blocking, fraud-like activity, complaints, and PII-sensitive cases should always require human review.

---

## 9. Data Sources

Use mock data only.

### Policy documents

Create markdown files:

```text
data/policies/
  withdrawal_policy.md
  deposit_policy.md
  bonus_policy.md
  login_policy.md
  account_verification_policy.md
  responsible_gaming_policy.md
  escalation_policy.md
```

Example policy content:

```markdown
# Withdrawal Policy

Repeated failed withdrawals must be treated as high priority.

Support agents must not tell the customer that the withdrawal is resolved unless payment status has been confirmed.

If a customer reports multiple failed withdrawal attempts in a short period, the case should be escalated to Payments Operations.
```

### Mock customer data

Use SQLite or JSON:

```text
data/mock/customers.json
data/mock/tickets.json
data/mock/transactions.json
data/mock/bonus_history.json
```

Example customer:

```json
{
  "customer_id": "CUST-1001",
  "name": "Example Customer",
  "account_status": "active",
  "verification_status": "verified",
  "risk_level": "medium",
  "recent_failed_withdrawals": 3,
  "active_bonus": false,
  "responsible_gaming_flag": false
}
```

---

## 10. Tools

Create LangChain tools.

### Read-only tools

```python
get_customer_profile(customer_id: str)
get_recent_transactions(customer_id: str)
get_ticket_history(customer_id: str)
get_bonus_status(customer_id: str)
search_policy_documents(query: str)
```

### Approval-required tools

These should not execute automatically.

```python
create_escalation_ticket(customer_id: str, reason: str)
draft_customer_reply(ticket_id: str, message: str)
mark_ticket_for_human_review(ticket_id: str, reason: str)
```

### Forbidden actions

Do not expose these to the agent:

```text
send_customer_message
close_customer_account
issue_refund
change_customer_status
delete_customer_data
```

The portfolio point is that the agent can **recommend** or **draft**, but not execute dangerous actions without approval.

---

## 11. Structured Outputs

Use Pydantic models.

### Ticket classification

```python
class TicketClassification(BaseModel):
    category: Literal[
        "withdrawal_issue",
        "deposit_issue",
        "login_issue",
        "bonus_issue",
        "account_verification",
        "responsible_gaming",
        "other",
    ]
    urgency: Literal["low", "medium", "high"]
    sentiment: Literal["positive", "neutral", "negative"]
    summary: str
    requires_human_review: bool
    sensitive_case: bool
    extracted_customer_id: str | None
```

### Policy-grounded recommendation

```python
class SupportRecommendation(BaseModel):
    recommended_action: str
    reason: str
    relevant_policy_sources: list[str]
    missing_information: list[str]
    human_review_required: bool
```

### Draft response

```python
class DraftResponse(BaseModel):
    customer_message: str
    tone: Literal["neutral", "empathetic", "formal"]
    should_send: bool
    approval_required: bool
    reason_approval_required: str | None
```

---

## 12. Human Approval Gate

The agent should stop before any customer-facing or escalation action.

Example:

```text
Proposed action:
Create escalation ticket for CUST-1001.

Reason:
Customer has 3 failed withdrawals in the last 24 hours.

Approval required:
Yes

Approve? [Approve] [Reject]
```

If approved:

```text
Mock escalation ticket created: ESC-1001
```

If rejected:

```text
Action not executed. Draft saved for review.
```

This is one of the most important features. It shows safe agent design.

---

## 13. UI Design

Use Streamlit for the first version.

### Layout

```text
Left column:
- Select mock customer
- Select issue type / sample message
- View customer profile

Middle column:
- Customer message input
- Run copilot button
- Classification result
- Suggested response

Right column:
- Policy evidence
- Tool results
- Human approval panel
- Audit trail
```

### Demo scenarios

Add buttons for:

```text
Failed withdrawal
Missing bonus
Account locked
Responsible gaming concern
Verification issue
Deposit delay
```

---

## 14. Evaluation Framework

Create 20–30 evaluation cases.

### Evaluation dimensions

```text
classification accuracy
policy retrieval relevance
groundedness
sensitive-case detection
human-review correctness
response quality
tool-selection correctness
```

### Example eval case

```json
{
  "id": "q01",
  "customer_message": "I tried to withdraw €200 three times and it keeps failing.",
  "expected_category": "withdrawal_issue",
  "expected_human_review": true,
  "expected_policy_source": "withdrawal_policy.md",
  "must_include": [
    "failed withdrawals",
    "human review",
    "payment status"
  ],
  "must_not_include": [
    "your withdrawal is resolved",
    "no action needed"
  ]
}
```

### LangSmith

Use LangSmith for:

```text
tracing
debugging tool calls
viewing graph runs
comparing prompt versions
running eval datasets
```

---

## 15. Testing

Add tests for:

```text
Pydantic schemas
ticket classification
policy retrieval
tool outputs
risk rules
approval gate
graph routing
eval runner
```

Example test files:

```text
tests/
  test_schemas.py
  test_policy_retrieval.py
  test_tools.py
  test_risk_rules.py
  test_graph.py
  test_evals.py
```

---

## 16. Project Structure

```text
customer-support-resolution-copilot/
│
├── app.py
├── main.py
├── pyproject.toml                  # Project metadata and dependencies managed by uv
├── uv.lock                         # Locked dependency versions generated by uv
├── README.md
├── .env.example
│
├── data/
│   ├── policies/
│   │   ├── withdrawal_policy.md
│   │   ├── deposit_policy.md
│   │   ├── bonus_policy.md
│   │   ├── login_policy.md
│   │   ├── account_verification_policy.md
│   │   └── responsible_gaming_policy.md
│   │
│   └── mock/
│       ├── customers.json
│       ├── tickets.json
│       ├── transactions.json
│       └── bonus_history.json
│
├── models/
│   ├── classification.py
│   ├── recommendation.py
│   └── response.py
│
├── graph/
│   ├── state.py
│   ├── graph.py
│   ├── nodes/
│   │   ├── classify_ticket.py
│   │   ├── retrieve_policy.py
│   │   ├── customer_context.py
│   │   ├── risk_check.py
│   │   ├── draft_response.py
│   │   ├── approval_gate.py
│   │   └── final_response.py
│   │
│   └── chains/
│       ├── classifier.py
│       ├── response_generator.py
│       └── groundedness_checker.py
│
├── tools/
│   ├── customer_tools.py
│   ├── ticket_tools.py
│   ├── transaction_tools.py
│   └── bonus_tools.py
│
├── rag/
│   ├── ingest.py
│   ├── retriever.py
│   └── vector_store.py
│
├── evals/
│   ├── dataset.py
│   ├── evaluators.py
│   └── run_evals.py
│
└── tests/
    ├── test_graph.py
    ├── test_tools.py
    ├── test_rag.py
    └── test_evals.py
```

---

## 17. MVP Build Plan

### Phase 0 — Project setup

Set up:

```text
uv-managed Python project
pyproject.toml
uv.lock
.env.example
pytest + ruff
base README instructions using uv sync / uv run
```

### Phase 1 — Basic workflow

Build:

```text
classification
policy RAG
mock customer lookup
draft response
Streamlit UI
```

### Phase 2 — LangGraph control

Add:

```text
conditional routing
risk check node
sensitive case route
approval gate
audit trail
```

### Phase 3 — Evaluation

Add:

```text
20 eval cases
classification evals
policy retrieval evals
human-review evals
LangSmith tracing
```

### Phase 4 — Polish

Add:

```text
README
screenshots
architecture diagram
graph diagram
demo scenarios
Docker setup
```

---

## 18. README Must Include

Your README should include:

```text
project overview
why this is not a generic chatbot
architecture diagram
LangGraph workflow diagram
example support scenarios
policy RAG explanation
tool list
approval gate explanation
evaluation results
screenshots
limitations
future improvements
uv setup instructions
```

---

## 19. Limitations to State Honestly

```text
Mock customer data only
Mock action execution only
No real support system integration
No automatic customer messaging
No legal/compliance decision-making
No production authentication
```

This is good. It shows responsible AI thinking.

---

## 20. Future Improvements

```text
Integrate with Zendesk or Intercom
Add multilingual support
Add voice-of-customer analytics
Add escalation queue
Add role-based access control
Add persistent Postgres database
Add real-time ticket ingestion
Add prompt/version regression testing
Add response caching
```

---

## 21. Final Portfolio Positioning

This project should show:

```text
I can build safe, workflow-based GenAI systems for business users.
I understand RAG, tool calling, structured outputs and LangGraph.
I know how to design approval gates and audit trails.
I can evaluate AI quality, not just generate responses.
```

Together with your sports project, your portfolio becomes:

```text
Streaming Sports Intelligence Agent
→ event-driven RAG, streaming ingestion, source-grounded analysis

Customer Support Resolution Copilot
→ business workflow AI, policy RAG, tool calling, human approval
```

That is a strong AI Engineer portfolio combination.
