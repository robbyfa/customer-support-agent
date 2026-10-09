"""Single-process local case service; checkpoints are the source of truth."""

import asyncio
import logging
from uuid import uuid4

from langgraph.types import Command

from graph.nodes.approval_gate import ReviewDecision
from storage.pii import mask_customer_context

logger = logging.getLogger(__name__)


class CaseNotFound(Exception):
    pass


class DecisionConflict(Exception):
    pass


def case_view(case_id, snapshot):
    state = snapshot.values
    interrupted = any(task.interrupts for task in snapshot.tasks)
    failed = any(task.error for task in snapshot.tasks)
    status = (
        "failed" if failed else "pending_review" if interrupted else
        "running" if snapshot.next else "approved" if state.get("approved") else "rejected"
    )
    # Never expose the raw checkpoint or unmasked customer context.
    output = {key: state.get(key) for key in (
        "customer_message", "customer_id", "classification", "policy_context",
        "risk_assessment", "recommendation", "draft_response", "approved",
    )}
    output["customer_context"] = mask_customer_context(state.get("customer_context") or {})
    output["status"] = status
    return {
        "id": case_id,
        "status": status,
        "review_decision": state.get("review_decision"),
        "final_output": state.get("final_output"),
        "preview": output,
        "groundedness_check": state.get("groundedness_check"),
        "audit_trail": state.get("audit_trail", []),
    }


class CaseService:
    def __init__(self, graph):
        self.graph = graph
        # Serialize mutations and reads for a consistent local demo. Run ONE worker.
        self._lock = asyncio.Lock()

    @staticmethod
    def config(case_id):
        return {"configurable": {"thread_id": case_id}}

    async def _get(self, case_id):
        snapshot = await self.graph.aget_state(self.config(case_id))
        if not snapshot.values:
            raise CaseNotFound(case_id)
        return case_view(case_id, snapshot)

    async def get(self, case_id):
        async with self._lock:
            return await self._get(case_id)

    async def create(self, customer_message, customer_id):
        case_id = str(uuid4())
        async with self._lock:
            try:
                await self.graph.ainvoke({
                    "customer_message": customer_message,
                    "customer_id": customer_id,
                    "audit_trail": [],
                    "draft_retries": 0,
                }, self.config(case_id))
            except Exception:
                # Error details may contain customer/provider data; do not expose them.
                logger.error("Case execution failed: %s", case_id)
                view = await self._get(case_id)
                view["status"] = "failed"
                return view
            return await self._get(case_id)

    async def decide(self, case_id, decision: ReviewDecision):
        async with self._lock:
            current = await self._get(case_id)
            if current["status"] != "pending_review":
                # Exact HTTP retries are safe; conflicting decisions cannot overwrite history.
                if current["review_decision"] == decision.model_dump() and current["status"] in {"approved", "rejected"}:
                    return current
                raise DecisionConflict("Case is not awaiting a decision")
            await self.graph.ainvoke(Command(resume=decision.model_dump()), self.config(case_id))
            return await self._get(case_id)
