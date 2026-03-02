# PySenior - AI-Powered Python Code Reviewer

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/your-org/pysenior)

**A Senior Python Engineer in your PRs 24/7**

PySenior is an AI-powered code review assistant that automatically reviews Python automation scripts in GitHub pull requests. It acts like a senior engineer with 10+ years of experience, identifying issues in reliability, security, performance, and maintainability.


## Features

### Intelligent Code Analysis
- **AI-Powered Reviews** - Uses GPT-4, Claude, Gemini, or 100+ models via OpenRouter
- **Automatic Detection** - Finds security vulnerabilities, performance issues, and reliability problems
- **Context-Aware** - Understands automation-specific concerns (shell safety, error handling, retries)

### Comprehensive Scoring
- **0-100 Score** - Weighted scoring across 4 dimensions
- **Letter Grades** - A+ to F grading system
- **Detailed Breakdown** - Per-category scores with issue counts
- **Severity Levels** - Critical, High, Medium, Low classifications

### GitHub Integration
- **Automatic Comments** - Posts review results directly on PRs
- **Inline Feedback** - Comments appear on specific code lines
- **Summary Scorecard** - Beautiful markdown table with all metrics
- **Webhook-Driven** - Triggered automatically on PR events

### Flexible LLM Support
- **OpenAI** - GPT-4o, GPT-4o-mini
- **Anthropic** - Claude 3.5 Sonnet, Opus
- **Google Gemini** - FREE tier with 1M tokens/day
- **Groq** - FREE & 10x faster (Llama, Mixtral)
- **OpenRouter** - Access to 100+ models with one API

### Focus Areas

**Security** (35% weight)
- SQL/Command injection detection
- Hardcoded credentials
- Unsafe file operations
- Shell execution risks

**Reliability** (30% weight)
- Error handling completeness
- Edge case coverage
- Input validation
- Resource cleanup

**Performance** (20% weight)
- Algorithmic complexity
- Memory efficiency
- Unnecessary operations
- Optimization opportunities

**Maintainability** (15% weight)
- Code clarity
- Documentation quality
- Function complexity
- Modularity

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- GitHub account with repository access
- API key for one of: [Gemini](https://makersuite.google.com/app/apikey) (FREE), [OpenAI](https://platform.openai.com), [Groq](https://console.groq.com) (FREE), or [OpenRouter](https://openrouter.ai)

### Installation (5 minutes)

```bash
# Clone the repository
git clone https://github.com/Err-Amon/Pysenior-AI-Assistent.git
cd Pysenior-AI-Assistent/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env` file:

```env
# GitHub
GITHUB_TOKEN=ghp_your_github_token_here

# LLM (choose one - Gemini is FREE!)
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy_your_gemini_key_here

# Webhook
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
```

**Get FREE Gemini API Key:** https://makersuite.google.com/app/apikey (no credit card needed!)

### Start Server

```bash
uvicorn app.main:app --reload
```

Server runs on http://localhost:8000

### Setup GitHub Webhook

1. Go to your repository → Settings → Webhooks → Add webhook
2. **Payload URL:** `https://your-domain.com/webhook/github`
3. **Content type:** `application/json`
4. **Secret:** Your `GITHUB_WEBHOOK_SECRET`
5. **Events:** Select "Pull requests" only
6. Click "Add webhook"

**For local testing:** Use [ngrok](https://ngrok.com) to create a public URL:
```bash
ngrok http 8000
# Use the ngrok URL in webhook settings
```

---

## Documentation

### For Users
- **[Complete Testing Guide](COMPLETE_TESTING_GUIDE.md)** - Step-by-step from scratch to working (30 min)
- **[User Guide](USER_GUIDE.md)** - Complete user manual with all features

### Architecture
- **[Architecture Overview](backend/README.md)** - System design
- **[Services Documentation](backend/app/services/README.md)** - Deep dive into services
- **[API Specification](backend/api_spec.md)** - API endpoints
- **[Data Flow](backend/data_flow.md)** - How data moves through the system

---

## Example Review

**Input:** Pull request with this code:

```python
import subprocess

def process_file(filename):
    subprocess.run(f"cat {filename}", shell=True)
    data = open(filename).read()
    query = f"SELECT * FROM users WHERE name = '{filename}'"
    return data
```

**Output:** PySenior automatically posts:

### Summary Comment
```
## PySenior Code Review

### Overall Score
🔴 45/100

### Score Breakdown
| Category | Score | Issues |
|----------|-------|--------|
| Reliability | 🟠 60/100 | 2 |
| Security | 🔴 30/100 | 3 |
| Performance | 🟢 85/100 | 0 |
| Maintainability | 🟡 70/100 | 1 |

### Critical Issues
- **process.py:4** - Shell injection vulnerability
- **process.py:6** - SQL injection risk
```

### Inline Comments

**Line 4:**
```
CRITICAL - Security

Shell injection vulnerability

Issue: Using shell=True with user input creates command injection risk.
An attacker could pass `; rm -rf /` to delete files.

Suggestion: Use list-based arguments instead:
subprocess.run(["cat", filename])
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     GitHub Webhook                      │
│              (PR opened/synchronized)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              GitHub Webhook Handler                     │
│         (Validates & extracts PR data)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │   GitHub Service           │
        │   - Fetch PR files         │
        │   - Filter Python files    │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │   Code Parser (AST)        │
        │   - Extract functions      │
        │   - Calculate complexity   │
        │   - Find line numbers      │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │   AI Review Service        │
        │   - Build prompts          │
        │   - Call LLM API           │
        │   - Parse findings         │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │   Scoring Service          │
        │   - Calculate scores       │
        │   - Apply weights          │
        │   - Generate grades        │
        └────────┬───────────────────┘
                 │
                 ▼
        ┌────────────────────────────┐
        │   Notification Service     │
        │   - Format comments        │
        │   - Post to GitHub         │
        └────────────────────────────┘
```

### Key Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Webhook Handler** | Receives GitHub events | FastAPI |
| **GitHub Service** | Interacts with GitHub API | PyGithub |
| **Code Parser** | Analyzes Python AST | Python AST module |
| **AI Review** | Generates findings | OpenAI/Anthropic/Gemini/Groq |
| **Scoring** | Calculates quality scores | Custom algorithm |
| **Notification** | Posts review comments | GitHub API |

---

## Testing

### Run Tests

```bash
# All tests (270+)
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Specific module
pytest tests/test_ai_review.py -v

# Using test runner
python run_tests.py --coverage
```

### Test Coverage

```
Module                          Coverage
─────────────────────────────────────────
app/models/pr_models.py           95%
app/models/review_models.py       95%
app/models/score_models.py        95%
app/services/github_service.py    92%
app/services/code_parser.py       96%
app/services/ai_review.py         90%
app/services/scoring.py           98%
app/services/notification.py      90%
─────────────────────────────────────────
TOTAL                             93%
```

270+ tests across all modules with 93% coverage!

---

## Cost Comparison

### Per 100 Code Reviews

| Provider | Model | Cost | Setup |
|----------|-------|------|-------|
| **Gemini** | Gemini Pro 1.5 | **FREE** | Easy |
| **Groq** | Llama 3.1 70B | **FREE** | Easy |
| **OpenRouter** | Llama 3.1 (free route) | **FREE** | Easy |
| OpenRouter | GPT-4o-mini | $0.15 | Easy |
| OpenRouter | Claude 3.5 Sonnet | $3-5 | Easy |
| OpenAI | GPT-4o-mini | $0.50 | Medium |
| OpenAI | GPT-4o | $3 | Medium |
| Anthropic | Claude 3.5 Sonnet | $3 | Medium |

**Recommended:** Start with Gemini (FREE) or Groq (FREE & fast) for testing, upgrade to Claude/GPT-4 for production.

---

## Configuration

### Environment Variables

```env
# Required
GITHUB_TOKEN=ghp_...              # GitHub API access
GITHUB_WEBHOOK_SECRET=...         # Webhook verification

# LLM Provider (choose one)
LLM_PROVIDER=gemini               # openai, anthropic, gemini, groq, openrouter

# LLM API Keys (based on provider)
GEMINI_API_KEY=AIzaSy...          # FREE - 1M tokens/day
GROQ_API_KEY=gsk_...              # FREE - 14.4K req/day
OPENROUTER_API_KEY=sk-or-v1-...   # $1 credit, 100+ models
OPENAI_API_KEY=sk-proj-...        # $5 free credits
ANTHROPIC_API_KEY=sk-ant-...      # Sometimes $5 free

# Optional
APP_ENV=development               # development, production
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
MAX_FILE_SIZE_KB=500              # Skip files larger than this
```

### Switching LLM Providers

```bash
# Use FREE Gemini
LLM_PROVIDER=gemini

# Use FREE Groq (super fast!)
LLM_PROVIDER=groq

# Use OpenRouter (100+ models)
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Use OpenAI
LLM_PROVIDER=openai

# Use Anthropic
LLM_PROVIDER=anthropic
```

No code changes needed - just update `.env` and restart!

---

## Scoring System

### Score Calculation

**Base:** 100 points per category

**Deductions:**
- Critical: -20 points
- High: -10 points
- Medium: -5 points
- Low: -2 points

**Category Weights:**
- Security: 35% (highest priority)
- Reliability: 30%
- Performance: 20%
- Maintainability: 15%

**Overall Score = Weighted Average**

### Grade Mapping

| Score | Grade |
|-------|-------|
| 95-100 | A+ |
| 90-94 | A |
| 85-89 | A- |
| 80-84 | B+ |
| 75-79 | B |
| 70-74 | B- |
| 65-69 | C+ |
| 60-64 | C |
| 50-59 | D |
| 0-49 | F |

---

## Deployment

### Railway (Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

### Render

1. Connect GitHub repository
2. Set environment variables
3. Deploy with one click

### Docker

```bash
# Build
docker build -t pysenior .

# Run
docker run -p 8000:8000 --env-file .env pysenior
```

### Heroku

```bash
heroku create pysenior-app
heroku config:set GITHUB_TOKEN=ghp_...
git push heroku main
```

---

### Quick Contribution Guide

```bash
# 1. Fork and clone
git clone https://github.com/Err-Amon/Pysenior-AI-Assistent.git

# 2. Create branch
git checkout -b feature/your-feature

# 3. Make changes and test
pytest tests/ -v

# 4. Commit and push
git commit -m "feat: add your feature"
git push origin feature/your-feature

# 5. Open Pull Request
# PySenior will review your code! 
```

---

## Troubleshooting

### Common Issues

**No comments on PR?**
- Check webhook is configured with green 
- Verify GitHub token has `repo` scope
- Check server logs: `tail -f logs/pysenior.log`
- Ensure Python files in PR (`.py` extension)


# Check .env file
cat .env | grep API_KEY
```

**Tests failing?**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run specific test to see details
pytest tests/test_specific.py -v
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- **FastAPI** - Modern Python web framework
- **PyGithub** - GitHub API wrapper
- **OpenAI** - GPT models
- **Anthropic** - Claude models
- **Google** - Gemini models
- **Groq** - Fast inference
- **OpenRouter** - Unified LLM API

## Stats

- **210+ Tests** with 93% coverage
- **5 LLM Providers** supported
- **100+ AI Models** via OpenRouter
- **4 Review Categories** analyzed
- **0-100 Scoring** system
- **A+ to F Grading**


- **100% Open Source**