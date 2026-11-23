"""Slack alert helper for P1 tickets.

Posts to the Slack incoming webhook in SLACK_WEBHOOK_URL. When the variable is
unset (local dev, CI, public demo), it runs in dry-run mode and never touches
the network.
"""

from __future__ import annotations

import logging
import os

import httpx

from app.triage import TicketIn, TicketTriageOut

logger = logging.getLogger(__name__)


def build_payload(ticket: TicketIn, result: TicketTriageOut) -> dict:
    return {
        "text": f":rotating_light: {result.priority.value} {result.category.value}: {ticket.subject}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{result.priority.value} · {result.category.value}* → `{result.assigned_queue}`\n"
                        f"*From:* {ticket.customer_email} ({ticket.plan.value})\n"
                        f"*Subject:* {ticket.subject}\n"
                        f"_{result.reason}_"
                    ),
                },
            }
        ],
    }


def notify_p1_alert(ticket: TicketIn, result: TicketTriageOut) -> dict:
    if result.priority.value != "P1":
        return {"sent": False, "reason": "not_p1"}
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        return {"sent": False, "reason": "dry_run"}
    try:
        r = httpx.post(url, json=build_payload(ticket, result), timeout=5)
        r.raise_for_status()
        return {"sent": True, "reason": "ok"}
    except httpx.HTTPError as exc:
        # Alerting must never break triage itself.
        logger.warning("Slack alert failed: %s", exc)
        return {"sent": False, "reason": "error"}
