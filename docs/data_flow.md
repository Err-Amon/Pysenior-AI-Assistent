# Data Flow

## Overview

This document traces every data transformation in the PySenior pipeline, from the moment GitHub fires a webhook to the moment inline review comments appear on the PR. Understanding this flow precisely is essential before writing any service code.

---

## Trigger: GitHub Webhook

When a developer opens or updates a pull request in a connected repository, GitHub sends an HTTP POST to the configured webhook URL. The payload is a JSON object containing the event type, repository metadata, PR number, and commit information.

### Incoming Request Shape

```
POST /webhook/github
X-GitHub-Event: pull_request
X-Hub-Signature-256: sha256=<hmac>

{
  "action": "opened",
  "number": 42,
  "repository": { "full_name": "org/repo" },
  "pull_request": {
    "title": "Refactor ETL scheduler",
    "user": { "login": "alice" },
    "head": { "sha": "abc123def456" }
  }
}
```

The route handler validates the HMAC signature against `GITHUB_WEBHOOK_SECRET`. Requests with an invalid or missing signature return `401` immediately. Events with actions other than `opened` or `synchronize` return `200` with no further processing.

---

## Step 1 — Fetch PR Files

**`github_webhook.py` → `github_service.py`**

The route handler calls `github_service` with the repository name and PR number. The service retrieves the list of changed files and fetches the raw content of each Python file. Non-Python files are filtered out at this stage.

### Output — List of `PRFile` objects

```json
[
  {
    "filename": "etl/scheduler.py",
    "content": "import os\ndef run_job():\n    ...",
    "patch": "@@ -12,7 +12,9 @@..."
  }
]
```

---

## Step 2 — AST Parsing

**`github_webhook.py` → `code_parser.py`**

Each Python file's content string is passed to the code parser. The parser uses Python's built-in `ast` module to walk the syntax tree and extract structural elements with their exact line positions.

### What Is Extracted

- Function definitions — name, `line_start`, `line_end`, argument count
- Class definitions — name, `line_start`, `line_end`
- For and while loops — line number, nesting depth
- Try/except blocks — presence and line number
- Import statements — module names

### Output — `ParsedFile` object

```json
{
  "filename": "etl/scheduler.py",
  "elements": [
    {
      "type": "function",
      "name": "run_job",
      "line_start": 12,
      "line_end": 48
    },
    {
      "type": "loop",
      "line_start": 27,
      "nesting_depth": 2
    }
  ]
}
```

The AST output is what gives the AI accurate line numbers. Without this step the LLM would guess line positions and be unreliable.

---

## Step 3 — AI Review Generation

**`github_webhook.py` → `ai_review.py`**

The parsed file structure and raw source code are combined into a structured prompt. The LLM is instructed to act as a senior Python engineer and return only a JSON array of findings.

### Prompt Strategy

- The system prompt defines the reviewer persona and enforces the output contract
- The user prompt includes the file name, raw source code, and parsed structure
- JSON mode is enforced — the model cannot return free-form text
- Temperature is set low to maximize consistency and predictability

### Output — List of `ReviewFinding` objects

```json
[
  {
    "line": 84,
    "severity": "high",
    "category": "security",
    "issue": "Unsafe subprocess usage",
    "suggestion": "Use list-based args instead of shell=True"
  },
  {
    "line": 27,
    "severity": "medium",
    "category": "performance",
    "issue": "Nested loop with O(n^2) complexity",
    "suggestion": "Consider set lookup or caching"
  }
]
```

---

## Step 4 — Score Computation

**`github_webhook.py` → `scoring.py`**

The findings array is passed to `scoring.py`. The scorer computes four independent category scores and one aggregate overall score. All scores start at 100 and are reduced based on finding severity and category.

### Deduction Table

| Category | High Severity | Medium Severity | Low Severity |
|---|---|---|---|
| Security | -20 points | -10 points | -3 points |
| Reliability | -15 points | -8 points | -2 points |
| Performance | -12 points | -6 points | -2 points |
| Maintainability | -10 points | -5 points | -1 point |

Scores are floored at 0 and cannot exceed 100. The overall score is the average of all four category scores.

### Output — `ScoreCard` object

```json
{
  "reliability": 88,
  "security": 60,
  "performance": 82,
  "maintainability": 90,
  "overall": 80
}
```

---

## Step 5 — Post Comments to GitHub

**`github_webhook.py` → `notification.py` → `github_service.py`**

`notification.py` takes the findings and score card and produces two types of GitHub output.

### Inline Comments

Each finding with a valid line number becomes an inline review comment on the exact diff line. The comment body includes the severity, category, issue description, and suggestion.

### Summary Comment

A single top-level PR comment is posted with the full `ScoreCard` and a count of findings per severity level. This gives the developer an immediate health snapshot without requiring them to read every inline comment first.

`notification.py` calls `github_service.post_inline_comment()` and `github_service.post_pr_comment()` — it never calls the GitHub API directly. All raw API mechanics stay inside `github_service`.

---

## End State

After the pipeline completes, the pull request in GitHub contains inline comments on problematic lines and a summary comment with the overall scores. The PySenior backend has returned `HTTP 200` to GitHub. No data has been written to any storage. The webhook cycle is complete and the system returns to idle.