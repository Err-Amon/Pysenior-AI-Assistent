# PySenior - AI Python Code Review Assistant - Usage Guide

## What is PySenior?
PySenior is an AI-powered code review assistant that analyzes GitHub Pull Requests (PRs) using Large Language Models (LLMs) to identify potential issues in Python code. It provides:
- Automated PR reviews with AI-generated feedback
- Code quality scoring (Security, Reliability, Performance, Maintainability)
- Detailed issue reports with severity levels
- Integration with GitHub via webhooks

## Prerequisites

### 1. Python Environment
- Python 3.10+ is required
- The project uses `uv` for package management (already configured)

### 2. Required Credentials
Create a `.env` file in the `backend` directory with the following:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# LLM Configuration (choose one or more)
LLM_PROVIDER=openai  # Options: openai, anthropic, gemini, groq
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional
GEMINI_API_KEY=your_gemini_api_key      # Optional
GROQ_API_KEY=your_groq_api_key          # Optional (Fast & Free)

# Application Settings
APP_ENV=development
LOG_LEVEL=INFO
MAX_FILE_SIZE_KB=500
```

### How to Obtain Credentials

#### GitHub Token
1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Click "Generate new token"
3. Select scopes: `repo` (full control of private repositories), `read:user`
4. Copy the generated token

#### LLM API Keys
- **OpenAI**: [OpenAI API Keys](https://platform.openai.com/account/api-keys)
- **Anthropic**: [Anthropic Console](https://console.anthropic.com/)
- **Google Gemini**: [Google AI Studio](https://makersuite.google.com/) (Free tier available)
- **Groq**: [Groq Console](https://console.groq.com/) (Free tier available, very fast)

## Installation & Setup

1. **Clone the Repository** (if not already done):
   ```bash
   git clone <your-repo-url>
   cd "PySenior AI Assistant"
   ```

2. **Install Dependencies**:
   The project uses `uv` for package management. Run:
   ```bash
   cd backend
   uv sync
   ```

3. **Run the Application**:
   ```bash
   cd backend
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Test the Health Endpoint**:
   Open your browser or use curl:
   ```bash
   curl http://localhost:8000/health
   ```
   You should get: `{"status":"healthy"}`

## Testing the Application

### Run All Tests
```bash
cd backend
uv run pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Code Parser Tests
uv run pytest tests/test_code_parser.py -v

# Scoring System Tests
uv run pytest tests/test_scoring.py -v

# AI Review Tests
uv run pytest tests/test_ai_review.py -v

# GitHub Service Tests
uv run pytest tests/test_github_service.py -v

# Notification Tests
uv run pytest tests/test_notification.py -v
```

## How It Works

### Architecture Overview
```
GitHub PR → Webhook → GitHub Service → Code Parser → AI Review → Scoring → Notification
```

1. **Webhook**: Listens for PR events from GitHub
2. **GitHub Service**: Fetches PR files and content
3. **Code Parser**: Analyzes Python code structure using AST
4. **AI Review**: Uses LLM to generate review findings
5. **Scoring**: Calculates code quality score based on findings
6. **Notification**: Posts results back to GitHub

## Using PySenior

### Option 1: GitHub Webhook Integration (Production)

1. **Expose Your Local Server (for testing)**:
   Use a tool like ngrok to create a public URL:
   ```bash
   ngrok http 8000
   ```
   This will give you a URL like `https://abc123.ngrok.io`

2. **Set Up GitHub Webhook**:
   - Go to your GitHub repository → Settings → Webhooks → Add webhook
   - **Payload URL**: `https://your-ngrok-url/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: The value you set in `GITHUB_WEBHOOK_SECRET`
   - **Events to trigger**: Select "Pull requests"

3. **Create a PR**:
   - Make changes to your Python code
   - Create a new Pull Request
   - PySenior will automatically analyze it and post comments


## PySenior Code Review

### Overall Score
87/100

### Score Breakdown
| Category | Score | Issues |
|----------|-------|--------|
| Security | 95/100 | 1 |
| Reliability | 85/100 | 3 |
| Performance | 90/100 | 2 |
| Maintainability | 80/100 | 4 |

### Issues Found
- **CRITICAL** - Security: Unsafe subprocess usage with shell=True
- **HIGH** - Reliability: Missing error handling for file operations
- **MEDIUM** - Performance: Inefficient loop structure
```

### Inline Comment
```markdown
CRITICAL - Security

### Unsafe subprocess usage

**Issue:**
Using `shell=True` introduces command injection risks...

**Suggestion:**
Use list-based arguments instead...
```

## Customization

### Scoring System
Edit `backend/app/services/scoring.py` to adjust:
- Deduction values per severity
- Category weights
- Score calculation logic

### AI Review Configuration
Edit `backend/app/services/ai_review.py` to:
- Change system prompt
- Adjust LLM parameters
- Add support for new LLM providers

### Supported LLM Providers
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google Gemini (Free tier available)
- Groq (Fast inference, free tier available)

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify GitHub token has correct scopes
   - Check LLM API keys are valid
   - Ensure `.env` file is in the correct location

2. **Webhook Not Triggering**:
   - Check ngrok tunnel is active
   - Verify webhook secret matches
   - Check GitHub webhook delivery status

3. **Slow AI Review**:
   - Try using Groq (faster) or reduce file size limit
   - Check LLM API rate limits

4. **No Findings Detected**:
   - Check if PR contains Python files
   - Verify LLM provider configuration
   - Try increasing log level to DEBUG

### Logging
Logs are printed to the console. To see detailed debug logs:
```bash
LOG_LEVEL=DEBUG uv run uvicorn app.main:app --reload
```

## Best Practices

1. **Start with Test PRs**: Test with small PRs to understand the system
2. **Review AI Findings**: Always verify AI-generated issues manually
3. **Customize Scoring**: Adjust scoring based on your team's priorities
4. **Set Thresholds**: Define minimum score requirements for PR approval
5. **Monitor Performance**: Track review times and false positives

## Architecture Deep Dive

### Services Layer
- **github_service.py**: Handles all GitHub API interactions
- **code_parser.py**: Python AST parser for code structure analysis
- **ai_review.py**: LLM integration and prompt engineering
- **scoring.py**: Score calculation and metrics
- **notification.py**: GitHub comment posting

### Data Models
- **PRFile**: Represents a file changed in PR
- **ParsedFile**: AST-parsed file with code structure
- **ReviewFinding**: Individual issue found by AI
- **ScoreCard**: Complete code quality assessment

## Contributing

For development:
1. Create a feature branch
2. Make changes
3. Run all tests
4. Create a PR

## License
MIT License - see LICENSE file

---
**PySenior - A Senior Python Engineer in your PRs 24/7**
