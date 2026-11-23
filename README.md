# Ticket Triage API

[![CI](https://github.com/nsriharshavardhan/ticket-triage-api/actions/workflows/ci.yml/badge.svg)](https://github.com/nsriharshavardhan/ticket-triage-api/actions/workflows/ci.yml)

**Live demo:** https://ticket-triage-api.onrender.com

A FastAPI service that turns free-text SaaS support tickets into **structured, validated routing decisions**:
category, priority (P1–P3), destination queue, confidence, the signals that triggered it, and a readable reason.

## Features

- **Pydantic v2 schemas** validate input (email, length limits, plan enum) and output, so bad payloads get a clear 422.
- **Deterministic, explainable rules.** Every decision lists its matched keywords and a reason, so it can be audited.
- **Delivery:** pytest suite, GitHub Actions CI (tests + Docker build), Dockerfile, and a one-click `render.yaml`.

## Priority rules

| Category | Queue | Priority |
|----------|-------|----------|
| security | `security-response` | **P1** always |
| outage | `sre-oncall` | **P1** for paid plans or urgent language, otherwise P2 |
| bug | `engineering-support` | P2 for paid plans or urgent language, otherwise P3 |
| billing / account_access | `billing-ops` / `tier1-support` | P2 for enterprise or urgent language, otherwise P3 |
| feature_request / how_to | `product-feedback` / `tier1-support` | P3 |

Keywords in the subject count double. Ties go to the more severe category.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/` | Browser demo form |
| POST | `/triage` | Triage one ticket |
| GET  | `/health` | Health check |

```bash
curl -X POST https://ticket-triage-api.onrender.com/triage \
  -H "Content-Type: application/json" \
  -d '{"customer_email":"ops@bigcorp.com.au","plan":"enterprise",
       "subject":"Production down - API returning 500",
       "body":"All users cannot access the app since 9am. Urgent!"}'
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload   # open http://127.0.0.1:8000
```

## Deploy (Render free tier)

1. Sign in to [Render](https://render.com) with GitHub, then choose **New → Blueprint** and pick this repo.
2. Render reads `render.yaml` and deploys. In the demo form, check that the "Enterprise outage" example comes back as **P1**.
