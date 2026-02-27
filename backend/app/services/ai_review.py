import json
import logging
from typing import List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-5.3-codex"

SYSTEM_PROMPT = """You are PySenior — a battle-hardened Senior Python Engineer with 15+ years of experience.
You specialize in Python automation scripts, DevOps tooling, data pipelines, and production systems.

For every review, you MUST identify:
1. Real bugs and logic errors
2. Security vulnerabilities (injections, unsafe deserialization, exposed secrets)
3. Performance issues (inefficient loops, memory leaks)
4. Maintainability improvements (naming, structure, error handling, logging)
5. What is done well

Format your response as JSON with this EXACT structure:
{
  "summary": "2-3 sentence overall assessment",
  "praise": ["what was done well"],
  "critical_issues": [
    {"line": <int or null>, "issue": "description", "fix": "concrete fix suggestion"}
  ],
  "warnings": [
    {"line": <int or null>, "issue": "description", "fix": "concrete fix suggestion"}
  ],
  "suggestions": [
    {"line": <int or null>, "issue": "description", "fix": "concrete fix suggestion"}
  ],
  "scores": {
    "reliability": <0-10>,
    "security": <0-10>,
    "performance": <0-10>,
    "maintainability": <0-10>
  }
}

Return ONLY valid JSON — no markdown, no extra text."""


class AIReviewService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://pysenior.dev",
            "X-Title": "PySenior",
        }

    async def review(
        self,
        filename: str,
        code: str,
        diff: str,
        ast_issues: List[str],
    ) -> dict:
        ast_summary = "\n".join(f"- {i}" for i in ast_issues) if ast_issues else "None detected."

        user_message = f"""## File: `{filename}`

### AST Pre-Analysis:
{ast_summary}

### Git Diff:
```diff
{diff[:3000] if diff else "Full file — no diff available"}
```

### Full Source Code:
```python
{code[:6000]}
```

Review this Python code as a senior engineer. Return ONLY valid JSON."""

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 2000,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                raw = data["choices"][0]["message"]["content"].strip()

                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]

                return json.loads(raw)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._fallback_review(ast_issues)
        except Exception as e:
            logger.error(f"AI review failed for {filename}: {e}")
            return self._fallback_review(ast_issues)

    def _fallback_review(self, ast_issues: List[str]) -> dict:
        return {
            "summary": "Automated AST analysis completed. AI review unavailable.",
            "praise": [],
            "critical_issues": [],
            "warnings": [{"line": None, "issue": i, "fix": "See issue description"} for i in ast_issues[:5]],
            "suggestions": [],
            "scores": {
                "reliability": 5.0,
                "security": 5.0,
                "performance": 5.0,
                "maintainability": 5.0,
            },
        }