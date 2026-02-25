# API Specification

## Overview

PySenior Phase 1 exposes two HTTP endpoints. Both are served by the FastAPI backend. There is no public-facing API in Phase 1 — these endpoints are consumed by GitHub's webhook system and internal monitoring tooling only.

| Method | Path | Purpose | Caller |
|---|---|---|---|
| GET | `/health` | Uptime check | Uptime monitoring |
| POST | `/webhook/github` | Receive GitHub PR events | GitHub webhook system |

---

## GET /health

### Purpose

Health check endpoint. Used by uptime monitoring services and load balancers to confirm the service is running and responsive.

### Authentication

None. This endpoint is intentionally public.

### Request

```
GET /health HTTP/1.1
Host: your-pysenior-instance.com
```

### Success Response — `200 OK`

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

### Error Responses

None. If the service is down there will be no response. The absence of a `200` is the failure signal.

---

## POST /webhook/github

### Purpose

Receives pull request events from GitHub and triggers the full review pipeline: file fetching, AST parsing, AI review, score computation, and comment posting.

### Authentication

GitHub signs every webhook payload using HMAC-SHA256. The signature is sent in the `X-Hub-Signature-256` header. PySenior validates this signature against the `GITHUB_WEBHOOK_SECRET` environment variable. Requests with an invalid or missing signature are rejected immediately with `401`.

### Required Headers

| Header | Description |
|---|---|
| `Content-Type` | Must be `application/json` |
| `X-GitHub-Event` | Event type — only `pull_request` is processed |
| `X-Hub-Signature-256` | HMAC-SHA256 of the raw request body using the webhook secret |
| `X-GitHub-Delivery` | Unique event ID assigned by GitHub — logged for tracing |

### Accepted Actions

Only the following `pull_request` actions trigger the review pipeline. All other actions return `200` with a skipped status immediately.

- `opened` — a new PR has been created
- `synchronize` — new commits have been pushed to an existing PR

### Request Body

Sent automatically by GitHub. PySenior reads the following fields:

```json
{
  "action": "opened",
  "number": 42,
  "repository": {
    "full_name": "org/repo-name"
  },
  "pull_request": {
    "title": "Refactor ETL scheduler",
    "user": { "login": "alice" },
    "head": { "sha": "abc123def456" }
  }
}
```

### Success Response — `200 OK`

Returned after the full pipeline has completed and comments have been posted to GitHub.

```json
{
  "status": "review_posted",
  "pr_number": 42,
  "repository": "org/repo-name",
  "scores": {
    "reliability": 88,
    "security": 60,
    "performance": 82,
    "maintainability": 90,
    "overall": 80
  },
  "findings_count": 5
}
```

### Skipped Response — `200 OK`

Returned when the event is valid but the action does not require processing.

```json
{
  "status": "skipped",
  "reason": "action_not_relevant"
}
```

### Error Responses

| Status Code | Condition | Response Body |
|---|---|---|
| `401` | Invalid or missing webhook signature | `{ "error": "invalid_signature" }` |
| `400` | Malformed JSON payload | `{ "error": "invalid_payload" }` |
| `422` | Missing required fields in payload | `{ "error": "missing_fields", "detail": "..." }` |
| `500` | Internal pipeline failure | `{ "error": "internal_error", "detail": "..." }` |

---

## Environment Variables

All configuration is loaded from environment variables via `config.py`. No secrets are hardcoded anywhere in the codebase.

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Yes | Personal access token for GitHub API calls |
| `GITHUB_WEBHOOK_SECRET` | Yes | Secret used to validate incoming webhook signatures |
| `OPENAI_API_KEY` | Yes | API key for LLM review generation |
| `OPENAI_MODEL` | No | Model name to use — defaults to `gpt-4o` |
| `LOG_LEVEL` | No | Logging verbosity — defaults to `INFO` |

---

## Rate Limiting and Retry Behavior

PySenior does not implement its own rate limiting in Phase 1. GitHub's webhook delivery system retries automatically if PySenior returns a non-2xx response. For GitHub API rate limits encountered inside `github_service.py`, the service raises an exception that surfaces as a `500` error — GitHub will retry the webhook delivery after its own backoff period.

---

## Webhook Configuration in GitHub

To connect a repository to PySenior, add a webhook in the repository settings with the following configuration:

- **Payload URL:** `https://your-instance.com/webhook/github`
- **Content type:** `application/json`
- **Secret:** the value set in `GITHUB_WEBHOOK_SECRET`
- **Events:** select Individual events and check Pull requests only