# Customer Support Resolution Copilot

> An AI-powered support workflow copilot using LangGraph, LangChain, RAG, and MCP to classify support cases, retrieve policy guidance, draft grounded responses, flag sensitive issues, and enforce human approval before customer-facing actions.

---

## Architecture

```
Support Agent UI (Streamlit)
      │
      ▼
FastAPI REST API → Case service
      │
      ▼
LangGraph Workflow ↔ SQLite checkpoints
      │
      ├── Classify Ticket (structured output)
      ├── Retrieve Policy (RAG with category filtering → ChromaDB)
      ├── Customer Context ──→ MCP Client
      │     │                    └── MCP Support Server
      │     │                          ├── get_customer_profile (tool)
      │     │                          ├── get_ticket_history (tool)
      │     │                          ├── get_recent_transactions (tool)
      │     │                          ├── get_bonus_status (tool)
      │     │                          └── policy:// (resources)
      │     └── (full or minimal for sensitive cases)
      ├── Risk Check (rule-based risk assessment)
      ├── Generate Resolution Plan (draft + recommendation)
      ├── Groundedness Check (dual: draft + recommendation)
      │     ├── Grounded → Approval Gate
      │     ├── Not grounded → Retry (max 2)
      │     └── Retries exhausted → Manual Review Response
      ├── Approval Gate (interrupt → persisted checkpoint → Command resume)
      ├── Audit Log (consolidated summary)
      └── Final Response
      │
      ▼
Audit trail + LangSmith trace
```

## LangGraph Workflow

```mermaid
graph TD
    Start --> classify_ticket
    classify_ticket --> retrieve_policy
    retrieve_policy -- sensitive --> minimal_customer_context
    retrieve_policy -- standard --> customer_context
    minimal_customer_context --> risk_check
    customer_context --> risk_check
    risk_check --> generate_resolution_plan
    generate_resolution_plan --> groundedness_check
    groundedness_check -- grounded --> approval_gate
    groundedness_check -- not grounded --> generate_resolution_plan
    groundedness_check -- retries exhausted --> manual_review_response
    manual_review_response --> approval_gate
    approval_gate -- no review needed --> audit_log
    approval_gate -- review required --> human[Persisted interrupt / human decision]
    human -- Command resume --> audit_log
    audit_log --> final_response
    final_response --> End
```

### Key design decisions

- **Conditional routing**: Responsible gaming cases fast-track through minimal context to prioritise safety over deep analysis.
- **Dual groundedness check**: Both the customer-facing draft and the internal recommendation are verified against policy before approval.
- **Manual review fallback**: If the LLM cannot produce a grounded response after 2 retries, a safe templated response is used instead.
- **PII masking**: Customer profile names and emails are masked in API previews and final output. Raw checkpoints remain local; see persistence limits below.

---

## What This Project Demonstrates

| Capability | Implementation |
|---|---|
| Structured classification | `TicketClassification` with 7 Literal categories via `with_structured_output` |
| RAG | ChromaDB vector store with markdown section-aware chunking and category metadata filtering |
| Tool calling | 5 LangChain tools for customer, ticket, transaction, bonus, and policy lookup |
| MCP | MCP server exposing tools + policy resources, connected via stdio client with langchain-mcp-adapters |
| Risk assessment | Rule-based engine with 5 priority-ordered risk rules |
| Response generation | Separate chains for customer draft (what to SAY) and internal recommendation (what to DO) |
| Groundedness checking | LLM-based verification of both outputs against policy context |
| Durable human-in-the-loop | LangGraph interrupt + SQLite checkpoint + audited approve/reject resume |
| Backend API | Async FastAPI endpoints, Pydantic contracts, service layer, idempotent decisions |
| CI and containers | Ruff, pytest, retrieval smoke evaluation, Docker build; separate API/UI services |
| Audit trail | Every node logs step name, timestamp, and key metadata |
| Evaluation framework | 25 eval cases, 5 evaluation dimensions, weighted aggregate scoring |
| Separation evals | 5 evaluators checking draft vs recommendation boundaries |
| LangSmith tracing | Full graph tracing when enabled via environment variables |

---

## Example Scenarios

### 1. Failed Withdrawal (CUST-1001)

> "I tried to withdraw €300 three times and it keeps failing."

- **Category**: withdrawal_issue | **Urgency**: high | **Sentiment**: negative
- **Risk**: high - 3 failed withdrawals + negative sentiment
- **Recommendation**: Escalate to Payments Operations, check payment provider status
- **Draft**: Empathetic tone, does not claim issue is resolved
- **Status**: Pending review (human approval required)

### 2. Self-Exclusion Request (CUST-1006)

> "I want to take a break from gambling."

- **Category**: responsible_gaming | **Urgency**: high | **Sensitive**: yes
- **Path**: Minimal context (fast-tracked, no transaction lookup)
- **Recommendation**: Immediate Responsible Gaming team review
- **Status**: Pending review (mandatory for all responsible gaming cases)

### 3. Bonus Not Applied (CUST-1004)

> "I signed up with WELCOME100 promo code but my bonus was not credited."

- **Category**: bonus_issue | **Urgency**: medium | **Sentiment**: negative
- **Recommendation**: Check bonus eligibility, verify promo code, check wagering status
- **Status**: May auto-approve if low risk

---

## Policy RAG

7 markdown policy documents are ingested into ChromaDB:

| Policy | Categories |
|---|---|
| `withdrawal_policy.md` | withdrawal_issue |
| `deposit_policy.md` | deposit_issue |
| `bonus_policy.md` | bonus_issue |
| `login_policy.md` | login_issue |
| `account_verification_policy.md` | account_verification |
| `responsible_gaming_policy.md` | responsible_gaming |
| `escalation_policy.md` | all categories |

**Chunking**: Split by markdown headings (not character count) so each chunk is a complete section with source and heading prefix.

**Retrieval**: Category metadata filtering first, with automatic fallback to unfiltered search.

---

## Tools

| Tool | Type | Description |
|---|---|---|
| `get_customer_profile` | Read-only | Customer profile, status, risk level, flags |
| `get_recent_transactions` | Read-only | Deposits, withdrawals, failed attempts |
| `get_ticket_history` | Read-only | Past and open support tickets |
| `get_bonus_status` | Read-only | Active bonuses, wagering progress |
| `search_policy_documents` | Read-only | RAG search over policy corpus |

The agent can **recommend** and **draft**. Approval records a human decision; this demo never sends messages, closes accounts, or issues refunds.

---

## MCP Server

The project includes a **Model Context Protocol (MCP) server** that exposes customer support data as a standard context interface. The LangGraph agent connects to it via an MCP client, demonstrating the MCP pattern for tool and resource access.

### MCP Tools (executable functions)

| Tool | Description |
|---|---|
| `get_customer_profile` | Customer profile, status, risk level, flags |
| `get_ticket_history` | Past and open support tickets |
| `get_recent_transactions` | Deposits, withdrawals, failed attempts |
| `get_bonus_status` | Active bonuses, wagering progress |

### MCP Resources (contextual data)

| URI | Description |
|---|---|
| `policy://list` | List all available policy documents |
| `policy://{filename}` | Retrieve a specific policy document by name |

### How it connects

```
LangGraph node (customer_context)
      │
      ▼
  MCP Client (mcp_server/client.py)
      │ stdio
      ▼
  MCP Server (mcp_server/server.py)
      │
      ├── Tools → storage/mock_data.py
      └── Resources → data/policies/*.md
```

Run the MCP server standalone:
```bash
uv run python mcp_server/server.py                        # stdio
uv run python mcp_server/server.py --transport http --port 8100  # HTTP
```

---

## Approval Gate

Reviewable cases suspend graph execution before the audit summary and final output:

```
Draft awaiting review: CUST-1001
Risk level: high
Human review required: yes

[✅ Approve]  [❌ Reject]
```

- **Approve** → Resume the checkpoint, record the decision, finish with `approved`.
- **Reject** → Resume the checkpoint, record the decision, finish with `rejected`.

Both paths retain the draft and reviewer rationale. No external action is executed.

---

## Evaluation

The checked-in [evaluation report](docs/evaluation-results.md) contains a real,
live 25-case workflow run, measured scores, generated outputs, and per-case failures.
The separate [retrieval smoke report](docs/retrieval-smoke-results.md) measures
retrieval with supplied categories. Run the no-key smoke
check with `uv run python -m evals.smoke`.

### Dataset
25 evaluation cases covering all 6 issue types plus edge cases.

### Dimensions (weighted aggregate)
| Dimension | Weight | Description |
|---|---|---|
| Classification accuracy | 0.25 | Category, urgency, sentiment match |
| Policy retrieval | 0.20 | Correct policy source in results |
| Sensitivity detection | 0.20 | Human review flag accuracy |
| Response quality | 0.20 | Keyword presence/absence in draft |
| Keywords | 0.15 | Key terms in classification summary |

### Separation evals
| Check | Description |
|---|---|
| `draft_is_customer_safe` | No forbidden phrases or internal language in draft |
| `recommendation_is_internal` | Action verbs present, not customer-facing text |
| `no_unconfirmed_actions` | Neither output claims completed actions |
| `missing_info_quality` | Populated and specific, not empty |
| `approval_correctness` | Matches expected review decision |

Run evals:
```bash
uv run python -m evals.run_evals                    # full suite
uv run python -m evals.run_evals --category withdrawal_issue
uv run python -m evals.run_evals --question q01
uv run python -m evals.run_evals --output docs/full-evaluation-results.json
uv run python -m evals.report                       # render saved results without API calls
```

---

## Setup

### Prerequisites
- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd customer-support-agent

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Run

```bash
# Start the API first (one worker)
uv run uvicorn backend.api:app --host 127.0.0.1 --port 8000 --workers 1

# In another terminal: CLI demo
uv run python main.py

# Or Streamlit UI
uv run streamlit run app.py

# Tests
uv run pytest -m "not llm" -v

# Linting
uv run ruff check .
```

### Durable approvals and API

Cases requiring review stop inside LangGraph's `interrupt()` before `audit_log`
and `final_response`. The API owns an `AsyncSqliteSaver` and uses the case UUID
as the graph `thread_id`. Approve/reject resumes that checkpoint with
`Command(resume=...)`; rejection produces a terminal `rejected` result. Cases
without review flags finish automatically. This follows the
[LangGraph interrupt contract](https://docs.langchain.com/oss/python/langgraph/interrupts).

| Endpoint | Behavior |
|---|---|
| `POST /cases` | Process a message until completion or human review; returns a case ID |
| `GET /cases/{id}` | Read saved status, masked preview, and final output if completed |
| `POST /cases/{id}/approve` | Resume with approval, reviewer name, and reason |
| `POST /cases/{id}/reject` | Resume with rejection, reviewer name, and reason |
| `GET /cases/{id}/audit` | Read the checkpoint's persisted audit trail |
| `GET /health` | Startup readiness check |

Interactive API documentation: [localhost:8000/docs](http://localhost:8000/docs).

```bash
curl -X POST http://127.0.0.1:8000/cases \
  -H 'Content-Type: application/json' \
  -d '{"customer_message":"I want to self-exclude","customer_id":"CUST-1006"}'
# Use the returned case ID:
curl -X POST http://127.0.0.1:8000/cases/CASE_ID/approve \
  -H 'Content-Type: application/json' \
  -d '{"reviewer":"Demo agent","reason":"Reviewed the policy and draft"}'
```

Streamlit calls this API over HTTP. Save its `?case=...` URL or enter the case ID
to reopen a pending case after restarting both services. No decision depends on
Streamlit session state. Exact decision retries are idempotent; conflicting or
inapplicable decisions return 409. Unknown cases return 404, invalid input 422.
Processing failures leave a readable `failed` checkpoint without exposing provider
error details. Interrupted execution from an abrupt crash outside the approval
gate may appear as `running`; automatic recovery of such runs is not implemented.

This is a local, single-worker demo. A service lock serializes execution and
reads; it does not coordinate multiple workers or replicas. The API has no
authentication, and reviewer names are self-reported. Add authenticated identity,
authorization, and database-backed concurrency control before exposing it to
other users. Approval records a decision only: it does not send messages, move
funds, or mutate customer accounts.

`CHECKPOINT_DB` defaults to `runtime/checkpoints.sqlite`. Checkpoints retain raw
customer messages and workflow context on disk, even though API previews and
final customer profiles are masked. Use only the synthetic data supplied here;
configure retention, encryption, and access controls for real customer data.

### Containers and CI

```bash
cp .env.example .env  # add your OpenAI key
docker compose up --build
```

The API and UI run as separate services. Both health checks use Python's standard
library, so the slim image does not need curl. A named volume preserves SQLite
checkpoints across container replacement; `docker compose down -v` removes them.
The image excludes `.env`, local checkpoints, and the virtual environment.

[CI workflow](.github/workflows/ci.yml) runs Ruff, all non-LLM tests, the retrieval
smoke evaluation, and a Docker build on pushes and pull requests. It uploads the
smoke report as a workflow artifact. A green GitHub check appears only after the
workflow has actually run in the remote repository.

### LangSmith tracing (optional)

Set these in your `.env` to enable tracing:

```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=customer-support-copilot
```

---

## Project Structure

```
customer-support-agent/
├── backend/                        # FastAPI endpoints and durable case service
├── app.py                          # Streamlit HTTP client
├── main.py                         # CLI entry point
├── pyproject.toml                  # Dependencies (managed by uv)
├── .env.example                    # Environment variable template
│
├── data/
│   ├── policies/                   # 7 markdown policy documents
│   └── mock/                       # Mock customer/ticket/transaction data
│
├── models/
│   ├── classification.py           # TicketClassification
│   ├── recommendation.py           # SupportRecommendation
│   └── response.py                 # DraftResponse
│
├── graph/
│   ├── state.py                    # GraphState TypedDict
│   ├── consts.py                   # Node name constants
│   ├── graph.py                    # LangGraph workflow assembly
│   ├── nodes/                      # 11 graph nodes
│   │   ├── classify_ticket.py
│   │   ├── retrieve_policy.py
│   │   ├── customer_context.py
│   │   ├── minimal_customer_context.py
│   │   ├── risk_check.py
│   │   ├── generate_resolution_plan.py
│   │   ├── groundedness_check.py
│   │   ├── manual_review_response.py
│   │   ├── approval_gate.py
│   │   ├── audit_log.py
│   │   └── final_response.py
│   └── chains/                     # LLM chains
│       ├── classifier.py
│       ├── response_generator.py
│       ├── recommendation_generator.py
│       └── groundedness_checker.py
│
├── tools/                          # LangChain tools
│   ├── registry.py
│   ├── customer_tools.py
│   ├── ticket_tools.py
│   └── policy_tools.py
│
├── storage/
│   ├── mock_data.py                # JSON data loading
│   ├── vector_store.py             # ChromaDB policy store
│   └── pii.py                      # PII masking utilities
│
├── mcp_server/
│   ├── server.py                   # MCP server (tools + resources)
│   └── client.py                   # MCP client wrapper
│
├── evals/
│   ├── dataset.py                  # 25 evaluation cases
│   ├── evaluators.py               # 5 evaluation dimensions
│   ├── separation_evals.py         # Draft vs recommendation boundary checks
│   └── run_evals.py                # CLI evaluation runner
│
├── tests/                          # Unit, checkpoint, API, UI, and integration tests
│   ├── test_schemas.py
│   ├── test_tools.py
│   ├── test_policy_retrieval.py
│   ├── test_risk_rules.py
│   ├── test_graph.py
│   └── test_evals.py
│
└── docs/
    ├── graph.mmd                   # Mermaid diagram source
    └── graph.png                   # Rendered workflow diagram
```

---

## Limitations

- **Mock data only** - no real customer database or support system integration
- **Mock action execution** - approve/reject is simulated, no real ticket creation
- **No real-time ingestion** - policy documents are static markdown files
- **No authentication** - no user roles or access control in the UI
- **PII masking is best-effort** - uses pattern-based masking, not a full PII detection system

---

## Tech Stack

| Component | Technology |
|---|---|
| Workflow orchestration | LangGraph |
| LLM framework | LangChain |
| LLM provider | OpenAI (gpt-4o-mini) |
| Structured output | Pydantic |
| Vector store | ChromaDB |
| Tracing | LangSmith |
| UI | Streamlit |
| Testing | pytest |
| Linting | Ruff |
| Package management | uv |
| MCP | mcp + langchain-mcp-adapters (FastMCP server, stdio client) |
