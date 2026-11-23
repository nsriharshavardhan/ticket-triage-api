"""Rule-based support ticket triage.

Turns a free-text support ticket into a structured, validated routing decision:
category, priority (P1-P3), destination queue, detected signals and a short
human-readable reason. The rules are deterministic and explainable, so every
decision can be audited. That matters when a misrouted P1 means an SLA breach.
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class Plan(str, Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class Category(str, Enum):
    outage = "outage"
    security = "security"
    bug = "bug"
    billing = "billing"
    account_access = "account_access"
    feature_request = "feature_request"
    how_to = "how_to"


class Priority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class TicketIn(BaseModel):
    customer_email: EmailStr
    subject: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=5000)
    plan: Plan = Plan.pro

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customer_email": "ops@bigcorp.com.au",
                    "subject": "Production down - API returning 500 for all users",
                    "body": "Since 9am our whole team cannot log in and the API returns 500 errors. This is urgent.",
                    "plan": "enterprise",
                }
            ]
        }
    }


class TicketTriageOut(BaseModel):
    category: Category
    priority: Priority
    assigned_queue: str
    confidence: float = Field(..., ge=0, le=1)
    signals: list[str]
    reason: str


# Keyword patterns per category. Order in CATEGORY_ORDER breaks ties: more severe first.
PATTERNS: dict[Category, list[str]] = {
    Category.outage: [
        r"\b(down|outage|offline|unavailable)\b", r"\b5\d\d\b", r"\bnot (loading|responding)\b",
        r"\b(all|every) (users?|customers?)\b", r"\bcannot access\b", r"\bproduction\b",
    ],
    Category.security: [
        r"\b(breach|hacked|compromised|phishing|vulnerability|leak(ed)?)\b",
        r"\bunauthori[sz]ed\b", r"\bsuspicious (login|activity)\b",
    ],
    Category.bug: [
        r"\b(bug|error|crash(es|ed)?|broken|exception|glitch)\b", r"\bnot working\b",
        r"\bdoesn'?t work\b", r"\bwrong\b",
    ],
    Category.billing: [
        r"\b(invoice|billing|charged?|refund|payment|credit card|subscription|gst|receipt)\b",
        r"\bdouble charged\b",
    ],
    Category.account_access: [
        r"\b(password|login|log in|sign in|2fa|locked out|sso|reset)\b",
    ],
    Category.feature_request: [
        r"\b(feature request|would be (great|nice)|please add|suggestion|wishlist|roadmap)\b",
        r"\bcan you add\b",
    ],
    Category.how_to: [r"\b(how (do|can|to)|where (is|can)|is it possible|guide|docs?)\b"],
}
CATEGORY_ORDER = list(PATTERNS)

QUEUES = {
    Category.outage: "sre-oncall",
    Category.security: "security-response",
    Category.bug: "engineering-support",
    Category.billing: "billing-ops",
    Category.account_access: "tier1-support",
    Category.feature_request: "product-feedback",
    Category.how_to: "tier1-support",
}

URGENCY = re.compile(r"\b(urgent|asap|immediately|critical|emergency|blocker|blocking)\b", re.I)


def _matches(text: str, category: Category) -> list[str]:
    hits = []
    for pattern in PATTERNS[category]:
        m = re.search(pattern, text, re.I)
        if m:
            hits.append(m.group(0).lower())
    return hits


def triage(ticket: TicketIn) -> TicketTriageOut:
    text = f"{ticket.subject}\n{ticket.body}"
    scores = {c: _matches(text, c) for c in CATEGORY_ORDER}
    # Subject keywords count double: customers usually put the real problem there.
    weighted = {c: len(h) + len(_matches(ticket.subject, c)) for c, h in scores.items()}

    best = max(CATEGORY_ORDER, key=lambda c: (weighted[c], -CATEGORY_ORDER.index(c)))
    if weighted[best] == 0:
        best = Category.how_to
    hits = scores[best]
    urgent = bool(URGENCY.search(text))

    # Priority rules (documented in README).
    paid = ticket.plan != Plan.free
    if best == Category.security:
        priority = Priority.P1
    elif best == Category.outage:
        priority = Priority.P1 if (paid or urgent) else Priority.P2
    elif best == Category.bug:
        priority = Priority.P2 if (paid or urgent) else Priority.P3
    elif best in (Category.billing, Category.account_access):
        priority = Priority.P2 if (ticket.plan == Plan.enterprise or urgent) else Priority.P3
    else:
        priority = Priority.P3

    total = sum(weighted.values()) or 1
    confidence = round(min(0.99, 0.5 + 0.5 * weighted[best] / total), 2) if weighted[best] else 0.4

    signals = hits + (["urgent language"] if urgent else []) + [f"plan:{ticket.plan.value}"]
    reason = (
        f"Classified as {best.value} from keywords {hits or ['none']}; "
        f"{ticket.plan.value} plan{' with urgent language' if urgent else ''} -> {priority.value}."
    )
    return TicketTriageOut(
        category=best,
        priority=priority,
        assigned_queue=QUEUES[best],
        confidence=confidence,
        signals=signals,
        reason=reason,
    )
