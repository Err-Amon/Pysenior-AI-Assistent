# System Architecture

## Overview

PySenior is a stateless webhook-driven SaaS backend built with FastAPI. It integrates with GitHub, analyzes Python pull request code using AST-based static analysis, sends structured code context to an LLM for senior-level review, computes measurable quality scores, and posts inline comments back to the PR — all without any persistent storage in Phase 1.

---

## Architectural Principles

The system is designed around four non-negotiable constraints:

**Single Responsibility** — every module has exactly one job. Routes handle HTTP. Services handle business logic. Models define data shapes. Config manages environment. No file does more than one of these things.

**Stateless Pipeline** — no database in Phase 1. Each webhook event is fully self-contained: it arrives, gets processed, and posts results. Nothing is stored between requests.

**Isolation Between Layers** — no service imports another service directly. All orchestration happens inside the route handler. This keeps each service independently testable and replaceable.

**Deterministic AI Output** — the LLM is always prompted to return structured JSON only, never free-form text. This prevents brittle parsing and ensures consistent behavior downstream.

---

## System Layers

| Layer | Files | Responsibility |
|---|---|---|
| Entry Point | `main.py`, `config.py` | Bootstrap server, load environment, wire routes |
| Routes | `github_webhook.py`, `health.py` | Receive HTTP, validate, delegate to services |
| Services | `github_service`, `code_parser`, `ai_review`, `scoring`, `notification` | All business logic — isolated and independently testable |
| Models | `pr_models`, `review_models`, `score_models` | Typed data contracts between all layers |

---

## Data Flow

Every review follows this exact sequence. No step can be skipped or reordered.

```
GitHub PR opened/updated
        |
        v
POST /webhook/github
        |
        v
github_webhook.py        -- validate signature, check action type
        |
        v
github_service.py        -- fetch changed Python files from GitHub API
        |
        v
code_parser.py           -- AST analysis, extract structure + line numbers
        |
        v
ai_review.py             -- build prompt, call LLM, parse JSON findings
        |
        v
scoring.py               -- compute Reliability, Security, Performance, Maintainability scores
        |
        v
notification.py          -- format and post inline + summary comments to PR
```

---

## Service Responsibilities

### `github_service.py`

Acts as the sole interface to the GitHub API. Handles authentication, rate limits, pagination, and error handling. Returns clean Python data structures, never raw API response objects. All other services are completely unaware of GitHub's API internals.

### `code_parser.py`

Performs pure static analysis using Python's built-in `ast` module. Takes raw source code as a string and returns a structured list of code elements with their types, names, and exact line ranges. This is critical because LLMs cannot reliably determine line positions on their own — AST parsing solves this deterministically and with zero external dependencies.

### `ai_review.py`

Manages all LLM interaction. Constructs a structured prompt that instructs the model to return JSON only. Parses and validates the response. Normalizes output to a consistent schema. This is the only layer that communicates with the external AI provider — swapping providers requires changes here only.

### `scoring.py`

Pure computational logic with no external dependencies. Accepts a list of review findings and returns a `ScoreCard`. Scores start at 100 and are reduced based on finding severity and category. All scoring formulas live here and nowhere else, making them straightforward to tune without touching any other layer.

### `notification.py`

High-level comment strategy layer. Decides how to group findings, how to avoid comment spam, and how to format the PR summary comment. Calls `github_service` for the actual API posting. This separation exists because formatting and delivery strategy is a distinct concern from raw API mechanics.

---

## What This Architecture Does Not Include in Phase 1

- No database — review results are not persisted. They exist in GitHub as PR comments only.
- No frontend dashboard — the React UI is a Phase 2 deliverable.
- No authentication layer — webhook secret validation covers Phase 1 security needs.
- No queue or async job processing — the pipeline runs synchronously per webhook event.
- No multi-provider support — one GitHub integration, one LLM provider.

---

## Technology Choices

| Technology | Choice | Reason |
|---|---|---|
| Web Framework | FastAPI | Async-ready, automatic OpenAPI docs, native Pydantic integration |
| Data Validation | Pydantic v2 | Type-safe models, automatic validation, clean error messages |
| GitHub Integration | PyGithub | Stable, well-maintained GitHub API client |
| AST Parsing | Python `ast` (stdlib) | Zero dependency, deterministic, built into Python |
| LLM Provider | OpenAI API | Reliable JSON mode, strong instruction-following capability |