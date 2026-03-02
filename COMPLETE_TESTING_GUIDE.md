# PySenior Complete Testing Guide
## From Zero to Working Code Reviews in 30 Minutes

This guide walks you through testing PySenior **from absolute scratch** - no assumptions about your setup.

---

## Prerequisites Check (2 minutes)

Before starting, make sure you have:

### 1. Python 3.11 or Higher

**Check your Python version:**
```bash
python --version
# or
python3 --version
```

**Should see:** `Python 3.11.x` or higher

**Don't have it?**
- **macOS:** `brew install python@3.11`
- **Ubuntu/Debian:** `sudo apt install python3.11`
- **Windows:** Download from python.org

### 2. Git Installed

**Check:**
```bash
git --version
```

**Don't have it?**
- **macOS:** `brew install git`
- **Ubuntu/Debian:** `sudo apt install git`
- **Windows:** Download from git-scm.com

### 3. A GitHub Account

If you don't have one, sign up at https://github.com

---

## Part 1: Get the Code (3 minutes)

### Step 1: Navigate to Your Projects Folder

```bash
# Create a projects folder if you don't have one
mkdir -p ~/projects
cd ~/projects
```

### Step 2: Get PySenior Code

**Option A: If you have the project already**
```bash
cd ai-python-reviewer/backend
```

**Option B: If you need to clone it**
```bash
git clone https://github.com/your-org/ai-python-reviewer.git
cd ai-python-reviewer/backend
```

### Step 3: Verify You're in the Right Place

```bash
# You should see these files:
ls

# Expected output:
# app/  tests/  requirements.txt  .env.example  run_tests.py  etc.
```

---

## Part 2: Setup Environment (5 minutes)

### Step 1: Create Virtual Environment

**What this does:** Creates an isolated Python environment so packages don't conflict with your system Python.

```bash
python3 -m venv venv
```

**You should see:** A new `venv/` folder created

### Step 2: Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

**You should see:** Your terminal prompt changes to show `(venv)` at the beginning

### Step 3: Verify Virtual Environment is Active

```bash
which python
# Should show: /path/to/your/project/venv/bin/python
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

**This will take 1-2 minutes.** You'll see packages being installed.

**Expected output (last few lines):**
```
Successfully installed fastapi-0.115.6 uvicorn-0.34.0 ...
```

### Step 5: Verify Installation

```bash
python -c "import fastapi; import github; print('All packages installed!')"
```

**Should see:** `All packages installed!`

---

## Part 3: Configure API Keys (7 minutes)

You need TWO API keys to test:
1. **GitHub Token** (to access GitHub)
2. **LLM API Key** (for AI reviews - we'll use FREE Gemini)

### Step 1: Create .env File

```bash
# Copy the example file
cp .env.example .env

# Open it in a text editor
nano .env
# Or use: code .env (VS Code), vim .env, etc.
```

### Step 2: Get GitHub Personal Access Token

**a) Go to GitHub Settings:**
- Visit: https://github.com/settings/tokens
- Or: Click your profile picture → Settings → Developer settings → Personal access tokens → Tokens (classic)

**b) Generate New Token:**
- Click **"Generate new token"** → **"Generate new token (classic)"**
- Name it: `PySenior Testing`
- Expiration: Select `30 days` (for testing)
- Select scopes:
  - **repo** (Full control of private repositories)
- Click **"Generate token"** at the bottom

**c) Copy the Token:**
- You'll see a token starting with `ghp_`
- **COPY IT IMMEDIATELY** (you won't see it again!)
- Example: `ghp_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz`

**d) Add to .env file:**
```env
GITHUB_TOKEN=ghp_your_actual_token_here
```

### Step 3: Get FREE Gemini API Key (Recommended)

**Why Gemini?** It's 100% FREE with no credit card needed!

**a) Go to Google AI Studio:**
- Visit: https://makersuite.google.com/app/apikey
- Sign in with your Google account

**b) Create API Key:**
- Click **"Create API key"**
- Copy the key (starts with `AIzaSy`)
- Example: `AIzaSyAbCd123456789EfGhIjKlMnOpQrStUvWxYz`

**c) Add to .env file:**
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy_your_actual_key_here
```

### Step 4: Generate Webhook Secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Copy the output** (random string like `kJ8xN2pL9qR4mT6vC1bZ3hF5gY7wQ0uI`)

**Add to .env:**
```env
GITHUB_WEBHOOK_SECRET=your_generated_secret_here
```

### Step 5: Verify Your .env File

Your `.env` should look like this (with your actual values):

```env
GITHUB_TOKEN=ghp_abc123...
GITHUB_WEBHOOK_SECRET=kJ8xN2pL9qR4...
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
```

**Save the file!** (Ctrl+X, then Y, then Enter in nano)

### Step 6: Install Gemini Package

```bash
pip install google-generativeai
```
---

## Part 5: Run Unit Tests (3 minutes)

Let's make sure everything works before starting the server.

### Step 1: Run All Tests

```bash
pytest tests/ -v
```

**Expected output:**
```
========================= test session starts =========================
collected 216 items

tests/test_pr_models.py::TestPRFile::test_create_valid_prfile PASSED
tests/test_pr_models.py::TestPRFile::test_prfile_with_optional_fields PASSED
...
tests/test_ai_review.py::TestGenerate::test_processes_parsed_files PASSED

========================= 216 passed in 10.23s =========================
```

**All tests should PASS.** If some fail, check error messages.

### Step 2: Check Test Coverage (Optional)

```bash
pytest tests/ --cov=app --cov-report=term
```

**Expected output:**
```
---------- coverage: platform darwin, python 3.11.2 ----------
Name                          Stmts   Miss  Cover
-------------------------------------------------
app/services/ai_review.py       240     24    90%
app/services/scoring.py          85      2    98%
...
-------------------------------------------------
TOTAL                           975     67    93%
```

---

## Part 6: Start the Server (1 minute)

### Step 1: Start PySenior

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Server is now running!** 

### Step 2: Test Health Endpoint

**Open a NEW terminal** (keep the server running in the first one)

**Activate the virtual environment again:**
```bash
cd ~/projects/ai-python-reviewer/backend
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**Test the server:**
```bash
curl http://localhost:8000/
```

**Expected output:**
```json
{
  "service": "PySenior",
  "tagline": "A Senior Python Engineer in your PRs 24/7",
  "status": "running",
  "version": "1.0.0"
}
```

**Also test health endpoint:**
```bash
curl http://localhost:8000/health/
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "PySenior",
  "version": "1.0.0",
  "timestamp": "2024-02-27T10:30:45.123456"
}
```

---

## Part 7: Setup GitHub Webhook (5 minutes)

Now let's connect PySenior to a GitHub repository.

### Option A: Test Locally with ngrok (Recommended for Testing)

**Step 1: Install ngrok**

**macOS:**
```bash
brew install ngrok
```

**Linux/Windows:**
Download from https://ngrok.com/download

**Step 2: Start ngrok**

**In a NEW terminal (keep server running):**
```bash
ngrok http 8000
```

**Expected output:**
```
Session Status    online
Account           your-email@example.com
Version           3.x.x
Region            United States (us)
Forwarding        https://abc123.ngrok.io -> http://localhost:8000
```

**IMPORTANT:** Copy the `https://abc123.ngrok.io` URL (yours will be different)

**Step 3: Configure GitHub Webhook**

a) **Go to your test repository** on GitHub
   - Use any repository you have admin access to
   - Or create a new test repo: https://github.com/new

b) **Navigate to Settings:**
   - Click **Settings** (in repository)
   - Click **Webhooks** (left sidebar)
   - Click **Add webhook**

c) **Configure webhook:**

| Field | Value |
|-------|-------|
| **Payload URL** | `https://abc123.ngrok.io/webhook/github` (use YOUR ngrok URL) |
| **Content type** | `application/json` |
| **Secret** | Paste your `GITHUB_WEBHOOK_SECRET` from `.env` |
| **Which events?** | Select "Let me select individual events" |
| **Events** |  Check only **Pull requests** |
| **Active** |  Checked |

d) **Click "Add webhook"**

e) **Verify webhook:**
   - You should see a green checkmark 
   - Click "Recent Deliveries" → You should see a `ping` event

### Option B: Deploy to Cloud (For Production)

See `USER_GUIDE.md` for deployment instructions to:
- Railway
- Render
- Heroku
- AWS/GCP/Azure

---

## Part 8: Create Test Pull Request (5 minutes)

Now the moment of truth - let's test it with actual code!

### Step 1: Create Test File with Intentional Issues

**In your test repository, create a new branch:**

```bash
# Clone your test repo if you haven't
git clone https://github.com/your-username/your-test-repo.git
cd your-test-repo

# Create a new branch
git checkout -b test-pysenior
```

**Create a test Python file with deliberate issues:**

```bash
cat > bad_script.py << 'EOF'
import subprocess
import os

def process_file(filename):
    # Bad: Shell injection vulnerability
    subprocess.run(f"cat {filename}", shell=True)
    
    # Bad: No error handling
    data = open(filename).read()
    
    # Bad: SQL injection risk
    query = f"SELECT * FROM users WHERE name = '{filename}'"
    
    # Bad: Hardcoded credentials
    password = "admin123"
    db.connect("localhost", "admin", password)
    
    return data

# Bad: No main guard
process_file("test.txt")
EOF
```

### Step 2: Commit and Push

```bash
git add bad_script.py
git commit -m "Add script with security issues for testing"
git push origin test-pysenior
```

### Step 3: Create Pull Request

**a) Go to your repository on GitHub**

**b) You'll see a banner:** "test-pysenior had recent pushes"
   - Click **"Compare & pull request"**

**c) Create the PR:**
   - Title: `Test PySenior Code Review`
   - Description: `Testing the AI code reviewer`
   - Click **"Create pull request"**

### Step 4: Watch the Magic Happen! 

**In your terminal running the server, you should see:**

```
INFO: POST /webhook/github 200 OK
INFO: Received webhook event | action=opened | pr=#1
INFO: Fetched PR | repo=your-username/your-test-repo | pr=#1
INFO: Calling LLM | provider=gemini
INFO: Gemini API call successful
INFO: Review posting completed | posted=5 | failed=0
```

**In the ngrok terminal, you should see:**
```
POST /webhook/github           200 OK
```

**On GitHub (refresh the PR page), you should see:**

1. **Summary Comment** with:
   - Overall score (probably 50-60/100 due to issues 🔴)
   - Score breakdown table
   - Critical issues listed
   - PySenior signature

2. **Inline Comments** on the code:
   - Line 5:  CRITICAL - Shell injection vulnerability
   - Line 9:  HIGH - Missing error handling
   - Line 12:  CRITICAL - SQL injection risk
   - Line 15:  CRITICAL - Hardcoded credentials

---

## Part 9: Verify Everything Works (2 minutes)

### Check 1: Server Logs

**Look for these key messages in your server terminal:**

```
 INFO: Received webhook event
 INFO: Fetched PR
 INFO: Calling LLM | provider=gemini
 INFO: Gemini API call successful
 INFO: Review posting completed
```

### Check 2: GitHub Comments

**On the PR page, verify:**

 Summary comment at the top with scorecard
 Inline comments on problematic lines
 Comments have severity icons
 Comments have suggestions for fixes

### Check 3: Review Quality

**Check if PySenior caught:**

 Shell injection (`shell=True`)
 SQL injection (string concatenation in SQL)
 Missing error handling (no try-except)
 Hardcoded credentials
 Missing `if __name__ == "__main__"` guard

---

## Part 10: Test with Good Code (Optional - 2 minutes)

Let's see what happens with **good** code:

### Step 1: Create Another Branch

```bash
git checkout main
git checkout -b test-good-code
```

### Step 2: Create Good Code

```bash
cat > good_script.py << 'EOF'
"""
Module for processing files safely.
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def process_file(filepath: Path) -> Optional[str]:
    """
    Process a file safely with proper error handling.
    
    Args:
        filepath: Path to the file to process
        
    Returns:
        File contents as string, or None if error occurs
    """
    try:
        # Validate file exists
        if not filepath.exists():
            logger.error("File not found: %s", filepath)
            return None
        
        # Read file safely
        with filepath.open('r', encoding='utf-8') as f:
            data = f.read()
        
        logger.info("Successfully processed file: %s", filepath)
        return data
        
    except IOError as e:
        logger.error("IO error reading file: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return None


def main():
    """Main entry point."""
    test_file = Path("test.txt")
    result = process_file(test_file)
    
    if result:
        print(f"Processed {len(result)} characters")
    else:
        print("Failed to process file")


if __name__ == "__main__":
    main()
EOF
```

### Step 3: Create PR

```bash
git add good_script.py
git commit -m "Add well-written Python script"
git push origin test-good-code
```

Create PR on GitHub → Watch PySenior review it

### Expected Result:

**Score:** 90-100/100 🟢
**Comments:** Maybe a few minor suggestions
**Summary:** "Great work! No critical issues found" or similar

---

## Troubleshooting Common Issues

### Issue 1: "GITHUB_TOKEN not configured"

**Fix:**
```bash
# Check your .env file
cat .env | grep GITHUB_TOKEN

# Should show: GITHUB_TOKEN=ghp_...
# If not, add it and restart server
```

### Issue 2: "GEMINI_API_KEY not configured"

**Fix:**
```bash
# Check your .env file
cat .env | grep GEMINI_API_KEY

# Add it if missing:
echo 'GEMINI_API_KEY=your_key_here' >> .env

# Restart server
```

### Issue 3: No Comments on PR

**Possible causes:**

**a) Webhook not configured:**
- Check GitHub Settings → Webhooks
- Verify green checkmark 
- Check Recent Deliveries for errors

**b) Server not receiving requests:**
- Check server logs for `POST /webhook/github`
- Verify ngrok is still running
- Check ngrok URL hasn't changed

**c) Wrong file type:**
- PySenior only reviews `.py` files
- Verify your test file ends with `.py`

**d) Check logs:**
```bash
# Look for errors
grep ERROR logs/pysenior.log

# Check what happened
tail -50 logs/pysenior.log
```

### Issue 4: "Module not found" Errors

**Fix:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 5: Tests Failing

**Fix:**
```bash
# Run specific failing test to see details
pytest tests/test_specific.py::TestClass::test_name -v

# Check if all dependencies installed
pip list

# Reinstall if needed
pip install -r requirements.txt --force-reinstall
```

---
## Next Steps

**Now that it's working:**

1. **Try different LLM providers:**
   ```bash
   # Try OpenRouter
   LLM_PROVIDER=openrouter
   
   # Try Groq (fast!)
   LLM_PROVIDER=groq
   ```

2. **Use on real repositories:**
   - Set up on your actual projects
   - Let it review real PRs

3. **Deploy to production:**
   - Use Railway, Render, or Heroku
   - Set up proper domain
   - Monitor usage

4. **Customize:**
   - Adjust scoring weights
   - Modify prompts
   - Add custom checks

---

## Getting Help

**If stuck:**

1. **Check logs:**
   ```bash
   tail -f logs/pysenior.log
   ```

2. **Run validator:**
   ```bash
   python validate_config.py
   ```

3. **Check documentation:**
   - `USER_GUIDE.md` - Complete user manual
   - `TESTING_GUIDE.md` - Test information
   - `FREE_LLM_OPTIONS.md` - LLM setup

4. **Common issues:**
   - API keys have no extra spaces
   - Virtual environment is activated
   - Port 8000 is not in use
   - ngrok is still running

---

## Congratulations! 

You've successfully:
- Set up PySenior from scratch
- Configured API keys
- Run all tests
- Started the server
- Connected to GitHub
- Got AI to review actual code

**You now have a working AI code reviewer!** 

---

**Total Time:** ~30 minutes
**Difficulty:** Beginner-friendly with step-by-step instructions
**Cost:** $0 (using free Gemini API)