import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.triage import Category, Plan, Priority, TicketIn, triage

client = TestClient(app)


def make(subject: str, body: str, plan: str = "pro") -> TicketIn:
    return TicketIn(customer_email="user@example.com", subject=subject, body=body, plan=plan)


OUTAGE = make("Production down - API returning 500", "Every request fails and all users cannot access the app. Urgent!", "enterprise")
BILLING = make("Charged twice on invoice", "Our credit card was double charged this month, please refund one payment.")
FEATURE = make("Suggestion: dark mode", "It would be great if you could add a dark mode. Is it on the roadmap?", "free")


def test_enterprise_outage_is_p1_to_sre():
    r = triage(OUTAGE)
    assert r.category == Category.outage
    assert r.priority == Priority.P1
    assert r.assigned_queue == "sre-oncall"
    assert "urgent language" in r.signals


def test_free_plan_outage_without_urgency_is_p2():
    r = triage(make("Site is down", "The dashboard is down for me since this morning.", "free"))
    assert (r.category, r.priority) == (Category.outage, Priority.P2)


def test_security_is_always_p1():
    r = triage(make("Suspicious login on our account", "We saw a suspicious login from overseas, account may be compromised.", "free"))
    assert (r.category, r.priority, r.assigned_queue) == (Category.security, Priority.P1, "security-response")


def test_billing_routes_to_billing_ops():
    r = triage(BILLING)
    assert (r.category, r.priority, r.assigned_queue) == (Category.billing, Priority.P3, "billing-ops")


def test_enterprise_billing_is_p2():
    r = triage(BILLING.model_copy(update={"plan": Plan.enterprise}))
    assert r.priority == Priority.P2


def test_feature_request_is_p3():
    r = triage(FEATURE)
    assert (r.category, r.priority) == (Category.feature_request, Priority.P3)


def test_unmatched_ticket_defaults_to_how_to():
    r = triage(make("Quick one", "Hello team, hope you are well today."))
    assert r.category == Category.how_to
    assert r.confidence < 0.5


@pytest.mark.parametrize(
    "payload",
    [
        {"customer_email": "not-an-email", "subject": "Help", "body": "Something long enough here"},
        {"customer_email": "a@b.com", "subject": "Hi", "body": "short"},
        {"customer_email": "a@b.com", "subject": "Help me", "body": "Something long enough", "plan": "gold"},
    ],
)
def test_invalid_payloads_rejected(payload):
    assert client.post("/triage", json=payload).status_code == 422


def test_triage_endpoint_and_demo_page():
    r = client.post("/triage", json=OUTAGE.model_dump(mode="json"))
    assert r.status_code == 200
    assert r.json()["priority"] == "P1"
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}
