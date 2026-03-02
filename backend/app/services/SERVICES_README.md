
# PySenior Services Module

This directory contains the business logic layer for the PySenior AI Code Review Assistant.

## Architecture Overview

The services layer follows strict separation of concerns:

- **Routes** → HTTP handling only
- **Services** → Business logic only  
- **Models** → Data structures only

No service module should import from routes. Services may import from other services and models.

## Service Modules

### 1. github_service.py
**Purpose:** All GitHub API interactions

**Key Functions:**
- `get_pull_request(repository, pr_number)` - Fetch PR object
- `get_pr_files(repository, pr_number)` - Get changed files with patches
- `get_file_content(repository, filepath, ref)` - Fetch file content at commit
- `post_review_comment(...)` - Post inline code comment
- `post_issue_comment(...)` - Post general PR comment

**Design Principles:**
- Returns clean Python data structures (PRFile), not GitHub SDK types
- Handles GitHub API pagination and rate limits
- Filters for Python files only
- Implements file size limits
- Logs all API calls for debugging

**Error Handling:**
- Logs errors with context
- Raises GithubException for critical failures
- Non-critical comment failures are logged but don't stop the pipeline

---

### 2. code_parser.py
**Purpose:** Python AST parsing and structural analysis

**Key Functions:**
- `parse(files)` - Entry point, parses multiple PR files
- `parse_python_file(filename, content)` - Parse single file with AST

**Output:** `ParsedFile` objects containing:
- Functions with line numbers, complexity, decorators
- Classes with methods
- Loops (for, while)
- Try-except blocks
- Import statements
- Syntax error detection

**Design Principles:**
- Uses Python's `ast` module for reliable parsing
- Captures line numbers for precise comment placement
- Calculates cyclomatic complexity for functions
- Detects `if __name__ == '__main__'` guards
- Handles syntax errors gracefully (returns partial results)

**Why This Matters:**
- LLMs cannot reliably determine line numbers
- AST parsing ensures accurate comment placement
- Structural information helps AI provide better context

---

### 3. ai_review.py
**Purpose:** LLM interaction and prompt engineering

**Key Functions:**
- `generate(parsed_files)` - Entry point, generates review findings
- `_build_system_prompt()` - Constructs AI role and instructions
- `_build_file_context(parsed_file)` - Creates structured file representation
- `_parse_ai_response(response_text, filename)` - Converts LLM JSON to ReviewFinding objects
- `_call_llm(prompt)` - Placeholder for actual LLM API call

**Output:** List of `ReviewFinding` objects

**Design Principles:**
- Forces structured JSON output from LLM
- System prompt defines senior engineer persona
- Includes entity context (functions, classes) with line numbers
- Handles malformed LLM responses gracefully
- Strips markdown code fences from JSON

**Prompt Strategy:**
- Focuses on automation-specific concerns (shell safety, error handling, retries)
- Requires: filename, line_number, severity, category, title, description, suggestion
- Prioritizes production failure prevention over style

**Integration Points:**
- Currently uses placeholder `_call_llm()` function
- In production: integrate OpenAI, Anthropic, or LangChain
- Should implement: rate limiting, retries, streaming, token management

---

### 4. scoring.py
**Purpose:** Convert AI findings into measurable metrics

**Key Functions:**
- `calculate(findings)` - Entry point, returns complete ScoreCard
- `_calculate_category_score(findings, category)` - Score per dimension
- `_calculate_overall_score(category_scores)` - Weighted aggregate

**Scoring Logic:**
```
Base score: 100
Deductions per severity:
  - Low: -2 points
  - Medium: -5 points
  - High: -10 points
  - Critical: -20 points

Overall score weights:
  - Security: 35%
  - Reliability: 30%
  - Performance: 20%
  - Maintainability: 15%
```

**Output:** `ScoreCard` with:
- Four category scores (0-100)
- Overall weighted score
- Detailed breakdown (issue counts, deductions)
- Severity distribution

**Design Principles:**
- Pure math - no external dependencies
- Easy to tune deduction values
- Security weighted highest (automation scripts often run with privileges)
- Floor at 0, ceiling at 100

---

### 5. notification.py
**Purpose:** Post review results back to GitHub

**Key Functions:**
- `post(repository, pr_number, findings, score_card)` - Entry point
- `_build_summary_comment(scorecard, findings)` - Formats PR summary
- `_build_inline_comment(finding)` - Formats line comments
- `_format_score_badge(score)` - Visual score indicators

**Output Format:**

**Summary Comment:**
```markdown
## PySenior Code Review

### Overall Score
92/100

### Score Breakdown
| Category | Score | Issues |
|----------|-------|--------|
| Reliability |  95/100 | 2 |
| Security |  85/100 | 3 |
...
```

**Inline Comment:**
```markdown
CRITICAL - Security

### Unsafe subprocess usage

**Issue:**
Using shell=True introduces command injection risks...

**Suggestion:**
Use list-based arguments instead...
```

**Design Principles:**
- Summary comment posted first (critical)
- Inline comment failures logged but don't stop pipeline
- Groups findings by file
- Limits summary to top 5 issues per severity
- Uses emoji badges for quick visual scanning

**Error Handling:**
- Summary failure raises exception (critical)
- Individual inline comment failures logged (non-critical)
- Returns posted/failed counts for monitoring

---

## Data Flow

```
webhook → github_service → code_parser → ai_review → scoring → notification
                ↓              ↓            ↓           ↓           ↓
           list[PRFile]  list[ParsedFile] list[Finding] ScoreCard  GitHub
```

## Testing Strategy

Each service should be unit tested independently:

1. **github_service:** Mock GitHub API responses
2. **code_parser:** Test with sample Python code snippets
3. **ai_review:** Mock LLM responses with known JSON
4. **scoring:** Test deduction math with various finding combinations
5. **notification:** Mock GitHub comment posting

Integration tests should verify the full pipeline.

## Configuration

Services access configuration via `app.config.get_settings()`:

- `GITHUB_TOKEN` - Required for GitHub API
- `MAX_FILE_SIZE_KB` - File size limit for parsing
- `LOG_LEVEL` - Logging verbosity

### Performance Optimizations:
- Parallel file parsing
- LLM request batching
- Caching for repeated reviews
- Incremental analysis (only changed functions)

## Dependencies

See `requirements.txt` for full list. Key dependencies:

- **PyGithub** - GitHub API client
- **ast** (stdlib) - Python parsing
- **pydantic** - Data validation
- **openai/anthropic** (optional) - LLM providers

## Logging

All services use Python's standard logging:

```python
logger = logging.getLogger(__name__)
```

Log levels:
- **INFO:** Normal operation (PR fetched, files parsed, review completed)
- **WARNING:** Non-critical issues (large file skipped, comment failed)
- **ERROR:** Critical failures (API errors, parsing failures)
- **DEBUG:** Detailed information (file contents, API responses)

---

## Quick Start

```python
# Example: Run the full pipeline
from app.services import github_service, code_parser, ai_review, scoring, notification

# 1. Fetch PR files
files = github_service.get_pr_files("owner/repo", 42)

# 2. Parse Python code
parsed = code_parser.parse(files)

# 3. Generate AI review
findings = ai_review.generate(parsed)

# 4. Calculate scores
scorecard = scoring.calculate(findings)

# 5. Post results
notification.post("owner/repo", 42, findings, scorecard)
```
---

**Maintainer Notes:**

This architecture is designed to be:
- **Testable** - Each layer mocked independently
- **Extensible** - Easy to add new checks, LLM providers, or VCS platforms
- **Observable** - Comprehensive logging at each step
- **Reliable** - Graceful error handling, no cascading failures

When modifying services, maintain the separation of concerns. Don't leak HTTP logic into services or GitHub SDK types into business logic.