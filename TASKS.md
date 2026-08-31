# Customer Support Resolution Agent - Build Tasks

> Component-by-component build plan. Each node is built end-to-end (model + chain + node + tests) before moving to the next. Graph assembly at the end.

---

## Phase 0 - Foundation

### Task 1: Project scaffolding, dependencies, and graph state ✅

- [x] Create `pyproject.toml` with all dependencies (langchain, langgraph, langchain-openai, langsmith, pydantic, chromadb, streamlit, python-dotenv) and dev deps (ruff, pytest, pytest-cov)
- [x] Create `.python-version` (3.12)
- [x] Create `.env.example` (OPENAI_API_KEY, MODEL_NAME, LANGCHAIN_TRACING_V2, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT)
- [x] Create `.gitignore`
- [x] Create all package directories with `__init__.py` files (models, graph, graph/nodes, graph/chains, tools, storage, evals, tests)
- [x] Create `graph/consts.py` - node name constants (CLASSIFY_TICKET, RETRIEVE_POLICY, CUSTOMER_CONTEXT, RISK_CHECK, DRAFT_RESPONSE, APPROVAL_GATE, FINAL_RESPONSE)
- [x] Create `graph/state.py` - `GraphState(TypedDict)` with all fields (customer_message, customer_id, classification, policy_context, customer_context, risk_assessment, recommendation, draft_response, approved, final_output, audit_trail)
- [x] Run `uv sync` - verify all imports resolve
- [x] Verify: `uv run python -c "import langchain, langgraph, pydantic, chromadb; print('OK')"`

### Task 2: Mock data and data loading layer ✅

- [x] Create `data/mock/customers.json` - 6 customers (CUST-1001 through CUST-1006), one per issue type
- [x] Create `data/mock/tickets.json` - 8–10 past tickets across customers
- [x] Create `data/mock/transactions.json` - transaction history (deposits, withdrawals, failed attempts)
- [x] Create `data/mock/bonus_history.json` - bonus records
- [x] Create `storage/mock_data.py` - load functions: `load_customers()`, `load_tickets()`, `load_transactions()`, `load_bonus_history()`, `get_customer()`, `get_customer_transactions()`, `get_customer_tickets()`, `get_customer_bonus()`
- [x] Write tests in `tests/test_tools.py` (initial) - verify counts, known customer lookup, unknown customer returns None
- [x] Verify: `uv run pytest tests/test_tools.py -v` passes

### Task 3: Policy documents and RAG vector store ✅

- [x] Create `data/policies/withdrawal_policy.md`
- [x] Create `data/policies/deposit_policy.md`
- [x] Create `data/policies/bonus_policy.md`
- [x] Create `data/policies/login_policy.md`
- [x] Create `data/policies/account_verification_policy.md`
- [x] Create `data/policies/responsible_gaming_policy.md`
- [x] Create `data/policies/escalation_policy.md`
- [x] Create `storage/vector_store.py` - `PolicyVectorStore` class (ingest_policies, search, reset) following SportVectorStore pattern
- [x] Write tests in `tests/test_policy_retrieval.py` - search "failed withdrawal" → withdrawal_policy.md, search "self-exclusion" → responsible_gaming_policy.md
- [x] Verify: `uv run pytest tests/test_policy_retrieval.py -v` passes

### Task 4: Tools - customer, ticket, and policy tools with registry ✅

- [x] Create `tools/registry.py` - `_vector_store` global, `configure()`, `get_vector_store()` with RuntimeError guard
- [x] Create `tools/customer_tools.py` - `@tool get_customer_profile()`, `@tool get_recent_transactions()`, `@tool get_bonus_status()`
- [x] Create `tools/ticket_tools.py` - `@tool get_ticket_history()`
- [x] Create `tools/policy_tools.py` - `@tool search_policy_documents()`
- [x] Create `tools/__init__.py` - `get_all_tools()`, re-export `configure`
- [x] Extend `tests/test_tools.py` - test each tool with known customer IDs, unknown customer, policy search
- [x] Verify: `uv run pytest tests/test_tools.py -v` passes

---

## Phase 1 - Components (node-by-node)

### Task 5: Component - classify_ticket

**Model:**
- [x] Create `models/classification.py` - `TicketClassification(BaseModel)` with category (7 Literal types), urgency, sentiment, summary, requires_human_review, sensitive_case, extracted_customer_id
- [x] Update `models/__init__.py` - export TicketClassification

**Chain:**
- [x] Create `graph/chains/classifier.py` - `classification_chain = prompt | llm.with_structured_output(TicketClassification)`
- [x] Update `graph/chains/__init__.py`

**Node:**
- [x] Create `graph/nodes/classify_ticket.py` - `def classify_ticket(state) -> dict` returning classification, customer_id, audit_trail
- [x] Update `graph/nodes/__init__.py` - export classify_ticket

**Tests:**
- [x] Add schema tests in `tests/test_schemas.py` - instantiation, Literal validation, optional fields, serialization
- [x] Add chain/node tests in `tests/test_graph.py` - "failed withdrawal" → withdrawal_issue/high/negative, "can't log in" → login_issue
- [x] Verify: `uv run pytest tests/test_schemas.py tests/test_graph.py -v` passes

### Task 6: Component - retrieve_policy ✅

**Node:**
- [x] Create `graph/nodes/retrieve_policy.py` - `def retrieve_policy(state) -> dict` returning policy_context, audit_trail
- [x] Update `graph/nodes/__init__.py` - export retrieve_policy

**Tests:**
- [x] Extend `tests/test_policy_retrieval.py` - test node with withdrawal_issue state → withdrawal_policy.md content, responsible_gaming state → responsible_gaming_policy.md content
- [x] Verify: `uv run pytest tests/test_policy_retrieval.py -v` passes

### Task 7: Component - customer_context ✅

**Node:**
- [x] Create `graph/nodes/customer_context.py` - `def get_customer_context(state) -> dict` returning customer_context (profile, transactions, tickets, bonus, flags), audit_trail
- [x] Update `graph/nodes/__init__.py` - export get_customer_context

**Tests:**
- [x] Extend `tests/test_graph.py` - CUST-1001 returns 3 failed withdrawals, empty customer_id returns error, unknown ID returns error
- [x] Verify: `uv run pytest tests/test_graph.py -v -k "customer_context"` passes

### Task 8: Component - risk_check ✅

**Node:**
- [x] Create `graph/nodes/risk_check.py` - `def risk_check(state) -> dict` with rule-based risk logic, returning risk_assessment, audit_trail
- [x] Update `graph/nodes/__init__.py` - export risk_check

**Tests:**
- [x] Create `tests/test_risk_rules.py` - test scenarios:
  - [x] Withdrawal + 3 failures + negative → high risk + human review
  - [x] Login + neutral → low/medium risk, no human review
  - [x] Responsible gaming → always high risk + human review
  - [x] Negative + high urgency → elevated risk
  - [x] sensitive_case=True → human review required
- [x] Verify: `uv run pytest tests/test_risk_rules.py -v` passes

### Task 9: Component - draft_response

**Models:**
- [x] Create `models/recommendation.py` - `SupportRecommendation(BaseModel)`
- [x] Create `models/response.py` - `DraftResponse(BaseModel)` with `format_text()` method
- [x] Update `models/__init__.py` - export both models

**Chains:**
- [x] Create `graph/chains/response_generator.py` - `response_chain = prompt | llm.with_structured_output(DraftResponse)`
- [x] Create `graph/chains/groundedness_checker.py` - `groundedness_chain` with `GroundednessCheck` model
- [x] Update `graph/chains/__init__.py`

**Node:**
- [x] Create `graph/nodes/draft_response.py` - `def draft_response(state) -> dict` returning draft_response, recommendation, audit_trail
- [x] Update `graph/nodes/__init__.py` - export draft_response

**Tests:**
- [x] Extend `tests/test_schemas.py` - SupportRecommendation and DraftResponse validation, format_text() output
- [x] Extend `tests/test_graph.py` - response chain with full context → approval_required=True for high-risk, empathetic tone for negative sentiment
- [x] Verify: `uv run pytest tests/test_schemas.py tests/test_graph.py -v -k "draft"` passes

### Task 10: Component - approval_gate and final_response ✅

**Nodes:**
- [x] Create `graph/nodes/approval_gate.py` - `def approval_gate(state) -> dict` returning approved (bool), audit_trail
- [x] Create `graph/nodes/final_response.py` - `def final_response(state) -> dict` assembling final_output, audit_trail
- [x] Update `graph/nodes/__init__.py` - export both

**Tests:**
- [x] Extend `tests/test_graph.py`:
  - [x] approval_gate: risk requires review → approved=False
  - [x] approval_gate: no review needed → approved=True
  - [x] final_response: assembles all state pieces into final_output with expected keys
- [x] Verify: `uv run pytest tests/test_graph.py -v -k "approval or final"` passes

---

## Phase 2 - Integration

### Task 11: LangGraph workflow assembly ✅

- [x] Create `graph/graph.py` - `build_graph()` wiring all 7 nodes in linear flow (START → classify → retrieve → context → risk → draft → approval → final → END)
- [x] Module-level `app = build_graph()` singleton
- [x] Full end-to-end integration test in `tests/test_graph.py` - invoke with "failed withdrawal" + CUST-1001, verify final_output has all expected keys and correct values
- [x] Verify: `uv run pytest tests/test_graph.py -v` passes (all tests)

### Task 12: CLI entry point (main.py)

### Task 12: CLI entry point (main.py) ✅

- [x] Create `main.py` - load dotenv, setup stores, ingest policies, configure tools
- [x] Define 6 demo scenarios (one per issue type)
- [x] Create `render_copilot_response()` for formatted terminal output
- [x] Run each scenario through `app.invoke()` and pretty-print
- [x] Verify: `uv run python main.py` runs all 6 scenarios successfully

### Task 13: Streamlit UI ✅

- [x] Create `app.py` with session state management (`init_session_state()`)
- [x] Setup functions: `setup_stores()`, `setup_agent()`
- [x] Sidebar: customer selector dropdown, customer profile display, 6 demo scenario buttons, suggested questions
- [x] Main area: message input + "Run Copilot" button
- [x] Results display: classification badges, policy evidence expander, customer context expander, risk assessment, recommendation, draft response
- [x] Approval section: Approve/Reject `st.button` pair when approval_required
- [x] Audit trail expander
- [x] Custom CSS for badges and styling
- [x] Verify: `uv run streamlit run app.py` - interactive demo works end-to-end

---

## Phase 3 - Evaluation

### Task 14: Evaluation dataset and framework

- [ ] Create `evals/dataset.py` - 20–25 eval cases covering all 6 issue types + edge cases
- [ ] Helpers: `get_dataset()`, `get_by_category()`, `get_by_expected_review()`
- [ ] Create `evals/evaluators.py` - 5 dimensions: classification accuracy, policy retrieval relevance, sensitive-case detection, response quality (LLM), keyword checks
- [ ] Weighted aggregate: `evaluate_response()` with classification(0.25) + retrieval(0.2) + sensitivity(0.2) + response_quality(0.2) + keywords(0.15)
- [ ] Create `evals/run_evals.py` - CLI runner with `--category`, `--question`, `--output` args, emoji-scored output, summary table
- [ ] Write tests in `tests/test_evals.py` - dataset validation, evaluator unit tests, aggregate scoring
- [ ] Verify: `uv run python -m evals.run_evals` runs full eval suite with summary report

---

## Phase 4 - Polish

### Task 15: Conditional routing (Phase 2 graph)

- [ ] Add `route_by_category()` routing function to `graph/graph.py`
- [ ] responsible_gaming → elevated risk path with mandatory human review
- [ ] Payment categories → transaction-heavy context
- [ ] Other categories → standard linear flow
- [ ] Use `add_conditional_edges` after classify_ticket
- [ ] Extend `tests/test_graph.py` - verify different categories follow different paths
- [ ] Verify: `uv run pytest tests/test_graph.py -v` passes

### Task 16: LangSmith tracing and audit trail polish

- [ ] Verify all nodes append to audit_trail with step name, timestamp, duration, key metadata
- [ ] Configure LangSmith tracing via env vars
- [ ] Polish audit trail display in Streamlit UI
- [ ] Print audit trail in main.py CLI output
- [ ] Verify: audit_trail contains entries for all 7 nodes after full graph run

### Task 17: README and documentation

- [ ] Write `README.md` - project overview, architecture diagram (mermaid), LangGraph workflow diagram (mermaid), example scenarios, policy RAG explanation, tool list, approval gate explanation, eval results, screenshots, limitations, future improvements, setup instructions
- [ ] Update `.env.example` with documented env vars
- [ ] Verify: README renders correctly, setup instructions work from scratch

### Task 18: Docker setup and final polish

- [ ] Create `Dockerfile` (Python 3.12 slim, uv, expose 8501)
- [ ] Create `docker-compose.yml` (single Streamlit service)
- [ ] Run `uv run ruff check --fix .` - full linting pass
- [ ] Run `uv run pytest -v` - full test suite passes
- [ ] Run `uv run python -m evals.run_evals` - capture results for README
- [ ] Verify: `docker compose up` launches Streamlit at localhost:8501

---

## Progress Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 0 - Foundation | Tasks 1–4 | ✅ Complete |
| Phase 1 - Components | Tasks 5–10 | ✅ Complete |
| Phase 2 - Integration | Tasks 11–13 | ✅ Complete |
| Phase 3 - Evaluation | Task 14 | ⬜ Not started |
| Phase 4 - Polish | Tasks 15–18 | ⬜ Not started |
