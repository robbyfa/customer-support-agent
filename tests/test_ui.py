"""Streamlit uses HTTP for both case processing and human decisions."""

import httpx
from streamlit.testing.v1 import AppTest


def test_ui_creates_and_resumes_case_via_api(monkeypatch):
    case = {
        "id": "148e9172-d80e-482d-94cc-6ed3648812ad",
        "status": "pending_review",
        "final_output": None,
        "preview": {
            "classification": {}, "risk_assessment": {}, "customer_context": {},
            "draft_response": {"customer_message": "We will review your request."},
        },
        "audit_trail": [],
    }
    requests = []

    def request(method, url, **kwargs):
        requests.append((method, url, kwargs.get("json")))
        if url.endswith("/approve"):
            case["status"] = "approved"
        return httpx.Response(200, json=case, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", request)
    app = AppTest.from_file("../app.py").run()
    app.text_area[0].input("Please help with my withdrawal")
    next(button for button in app.button if button.label == "🚀 Run Copilot").click().run()
    assert not app.exception
    assert requests[0][0] == "POST"
    assert requests[0][1].endswith("/cases")
    next(field for field in app.text_input if field.label == "Reviewer name").input("Agent")
    next(field for field in app.text_area if field.label == "Decision reason").input("Checked policy")
    app.run()
    next(button for button in app.button if button.label == "✅ Approve").click().run()
    assert not app.exception
    assert requests[-1][1].endswith(f"/cases/{case['id']}/approve")
    assert requests[-1][2] == {"reviewer": "Agent", "reason": "Checked policy"}
    assert any("Response approved" in message.value for message in app.success)
