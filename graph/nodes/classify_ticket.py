"""Node: classify_ticket — classifies a customer message into a structured
TicketClassification and extracts the customer ID if present.
"""

from datetime import datetime, timezone
from typing import Any

from graph.chains.classifier import get_classification_chain
from graph.state import GraphState


def classify_ticket(state: GraphState) -> dict[str, Any]:
    """Classify the incoming customer message.

    Reads ``customer_message`` from state and returns:
    - classification: dict representation of TicketClassification
    - customer_id: extracted customer ID (may be None)
    - audit_trail: appended entry for this step
    """
    chain = get_classification_chain()
    result = chain.invoke({"customer_message": state["customer_message"]})

    classification = result.model_dump()

    audit_entry = {
        "step": "classify_ticket",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "category": classification["category"],
        "urgency": classification["urgency"],
        "sentiment": classification["sentiment"],
    }

    return {
        "classification": classification,
        "customer_id": classification.get("extracted_customer_id") or state.get("customer_id"),
        "audit_trail": state.get("audit_trail", []) + [audit_entry],
    }
