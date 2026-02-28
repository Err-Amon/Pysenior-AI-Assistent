import json
import logging
import time
from typing import Any

from app.models.review_models import Category, ReviewFinding, ReviewResult, Severity
from app.services.code_parser import CodeEntity, ParsedFile
from app.config import get_settings

# LLM Provider Imports (at module level to support mocking in tests)
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# LLM Provider Configuration
LLM_PROVIDER = "openai"  # Options: "openai", "anthropic", "gemini", "groq"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def _build_system_prompt() -> str:

    return """You are a senior Python engineer with 10+ years of experience reviewing automation code.

Your role is to review Python code for automation scripts, focusing on:

1. Reliability - Error handling, edge cases, robustness
2. Security - Shell injections, unsafe operations, credential handling
3. Performance - Inefficient loops, memory usage, unnecessary operations
4. Maintainability - Code clarity, modularity, documentation

For each issue you find:
- Identify the exact line number
- Classify severity: low, medium, high, critical
- Classify category: reliability, security, performance, maintainability
- Provide a clear title (1-2 sentences)
- Explain the issue in detail
- Give an actionable suggestion to fix it

Return your response as a JSON array of findings. Each finding must have:
{
  "filename": "path/to/file.py",
  "line_number": 42,
  "severity": "high",
  "category": "security",
  "title": "Brief issue description",
  "description": "Detailed explanation of why this is problematic",
  "suggestion": "Specific recommendation to fix the issue"
}

Focus on automation-specific concerns:
- Shell command execution safety
- File operation error handling
- API retry logic
- Resource cleanup
- Logging practices
- Configuration management

Be strict but fair. Only report actual issues, not stylistic preferences.
Prioritize issues that could cause production failures.
"""


def _build_file_context(parsed_file: ParsedFile) -> str:

    context_parts = [
        f"File: {parsed_file.filename}",
        f"Total lines: {parsed_file.total_lines}",
        f"Imports: {', '.join(parsed_file.imports[:10])}",  # Limit imports to avoid token waste
        "",
        "Code Structure:",
    ]

    # Add entity information
    for entity in parsed_file.entities:
        entity_desc = f"- {entity.entity_type} '{entity.name}' (lines {entity.line_start}-{entity.line_end})"

        if entity.complexity:
            entity_desc += f" [complexity: {entity.complexity}]"

        if entity.docstring:
            # Truncate long docstrings
            docstring_preview = (
                entity.docstring[:100] + "..."
                if len(entity.docstring) > 100
                else entity.docstring
            )
            entity_desc += f" - {docstring_preview}"

        context_parts.append(entity_desc)

    context_parts.extend(
        ["", "Full Code:", "```python", parsed_file.raw_content, "```"]
    )

    return "\n".join(context_parts)


def _parse_ai_response(response_text: str, filename: str) -> list[ReviewFinding]:

    findings = []

    try:
        # Try to extract JSON from response
        # LLMs sometimes wrap JSON in markdown code blocks
        cleaned = response_text.strip()

        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json")
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```")
        if cleaned.endswith("```"):
            cleaned = cleaned.removesuffix("```")

        cleaned = cleaned.strip()

        # Parse JSON
        raw_findings = json.loads(cleaned)

        if not isinstance(raw_findings, list):
            logger.warning("AI response is not a list | filename=%s", filename)
            return []

        # Convert each finding to ReviewFinding
        for item in raw_findings:
            try:
                finding = ReviewFinding(
                    filename=item.get("filename", filename),
                    line_number=item["line_number"],
                    severity=Severity(item["severity"].lower()),
                    category=Category(item["category"].lower()),
                    title=item["title"],
                    description=item["description"],
                    suggestion=item["suggestion"],
                    code_snippet=item.get("code_snippet"),
                )
                findings.append(finding)

            except (KeyError, ValueError) as e:
                logger.warning(
                    "Skipping malformed finding | filename=%s | error=%s | item=%s",
                    filename,
                    str(e),
                    item,
                )
                continue

    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse AI response as JSON | filename=%s | error=%s",
            filename,
            str(e),
        )

    return findings


def _call_llm_openai(system_prompt: str, user_prompt: str) -> str:

    if openai is None:
        raise ImportError(
            "OpenAI package not installed. Install with: pip install openai"
        )

    settings = get_settings()
    openai_api_key = getattr(settings, "OPENAI_API_KEY", None)

    if not openai_api_key:
        logger.error("OPENAI_API_KEY not configured")
        raise ValueError("OPENAI_API_KEY environment variable is required")

    # Initialize OpenAI client (v1.0+ API)
    client = openai.OpenAI(api_key=openai_api_key)

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling OpenAI API | attempt=%s | model=gpt-4o",
                attempt + 1,
            )

            response = client.chat.completions.create(
                model="gpt-4o",  # Use latest GPT-4o model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,  # Low temperature for consistent, focused reviews
                max_tokens=4000,  # Enough for detailed reviews
                response_format={"type": "json_object"},  # Force JSON output
            )

            content = response.choices[0].message.content

            logger.info(
                "OpenAI API call successful | tokens_used=%s",
                response.usage.total_tokens,
            )

            return content

        except openai.RateLimitError as e:
            logger.warning(
                "OpenAI rate limit hit | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            if attempt < MAX_RETRIES - 1:
                sleep_time = RETRY_DELAY * (2**attempt)  # Exponential backoff
                logger.info("Retrying after %s seconds...", sleep_time)
                time.sleep(sleep_time)
            else:
                raise

        except openai.APIError as e:
            logger.error(
                "OpenAI API error | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

        except Exception as e:
            logger.error(
                "Unexpected error calling OpenAI | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            raise


def _call_llm_anthropic(system_prompt: str, user_prompt: str) -> str:

    if anthropic is None:
        raise ImportError(
            "Anthropic package not installed. Install with: pip install anthropic"
        )

    settings = get_settings()
    anthropic_api_key = getattr(settings, "ANTHROPIC_API_KEY", None)

    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not configured")
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=anthropic_api_key)

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling Anthropic API | attempt=%s | model=claude-sonnet-4-20250514",
                attempt + 1,
            )

            # Note: Claude requires JSON instruction in user message
            # since it doesn't have native JSON mode
            json_instruction = "\n\nIMPORTANT: Return ONLY a valid JSON array. No markdown, no explanations, just the JSON array."

            response = client.messages.create(
                model="claude-sonnet-4-20250514",  # Latest Claude Sonnet
                max_tokens=4000,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt + json_instruction}],
            )

            content = response.content[0].text

            logger.info(
                "Anthropic API call successful | input_tokens=%s | output_tokens=%s",
                response.usage.input_tokens,
                response.usage.output_tokens,
            )

            return content

        except anthropic.RateLimitError as e:
            logger.warning(
                "Anthropic rate limit hit | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            if attempt < MAX_RETRIES - 1:
                sleep_time = RETRY_DELAY * (2**attempt)
                logger.info("Retrying after %s seconds...", sleep_time)
                time.sleep(sleep_time)
            else:
                raise

        except anthropic.APIError as e:
            logger.error(
                "Anthropic API error | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

        except Exception as e:
            logger.error(
                "Unexpected error calling Anthropic | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            raise


def _call_llm_gemini(system_prompt: str, user_prompt: str) -> str:

    if genai is None:
        raise ImportError(
            "Google Generative AI package not installed. "
            "Install with: pip install google-generativeai"
        )

    settings = get_settings()
    gemini_api_key = getattr(settings, "GEMINI_API_KEY", None)

    if not gemini_api_key:
        logger.error("GEMINI_API_KEY not configured")
        raise ValueError("GEMINI_API_KEY environment variable is required")

    # Configure Gemini
    genai.configure(api_key=gemini_api_key)

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling Gemini API | attempt=%s | model=gemini-1.5-flash",
                attempt + 1,
            )

            model = genai.GenerativeModel("gemini-1.5-flash")

            # Combine prompts with JSON instruction
            full_prompt = (
                f"{system_prompt}\n\n"
                f"{user_prompt}\n\n"
                f"IMPORTANT: Return ONLY a valid JSON array. "
                f"No markdown, no explanations, just the JSON array."
            )

            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=4000,
                ),
            )

            content = response.text

            logger.info("Gemini API call successful")

            return content

        except Exception as e:
            logger.error(
                "Gemini API error | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


def _call_llm_groq(system_prompt: str, user_prompt: str) -> str:

    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Groq package not installed. Install with: pip install groq")

    settings = get_settings()
    groq_api_key = getattr(settings, "GROQ_API_KEY", None)

    if not groq_api_key:
        logger.error("GROQ_API_KEY not configured")
        raise ValueError("GROQ_API_KEY environment variable is required")

    # Initialize Groq client
    client = Groq(api_key=groq_api_key)

    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(
                "Calling Groq API | attempt=%s | model=llama-3.3-70b-versatile",
                attempt + 1,
            )

            # Add JSON instruction to user prompt
            json_instruction = (
                "\n\nIMPORTANT: Return ONLY a valid JSON array. "
                "No markdown, no explanations, just the JSON array."
            )

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Fast & capable model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt + json_instruction},
                ],
                temperature=0.2,
                max_tokens=4000,
            )

            content = response.choices[0].message.content

            logger.info(
                "Groq API call successful | tokens_used=%s",
                response.usage.total_tokens if hasattr(response, "usage") else "N/A",
            )

            return content

        except Exception as e:
            logger.error(
                "Groq API error | attempt=%s | error=%s",
                attempt + 1,
                str(e),
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


def _call_llm(prompt: str) -> str:

    settings = get_settings()

    # Allow override via environment variable
    provider = getattr(settings, "LLM_PROVIDER", LLM_PROVIDER).lower()

    # Split prompt into system and user parts
    # The prompt format is: "<system_prompt>\n\n<file_context>"
    parts = prompt.split("\n\n", 1)
    if len(parts) == 2:
        system_prompt, user_prompt = parts
    else:
        # Fallback if format is unexpected
        system_prompt = _build_system_prompt()
        user_prompt = prompt

    logger.info("Calling LLM | provider=%s", provider)

    try:
        if provider == "openai":
            return _call_llm_openai(system_prompt, user_prompt)
        elif provider == "anthropic":
            return _call_llm_anthropic(system_prompt, user_prompt)
        elif provider == "gemini":
            return _call_llm_gemini(system_prompt, user_prompt)
        elif provider == "groq":
            return _call_llm_groq(system_prompt, user_prompt)
        else:
            raise ValueError(
                f"Invalid LLM provider: {provider}. "
                "Valid options: 'openai', 'anthropic', 'gemini', 'groq'"
            )

    except ImportError as e:
        logger.error("LLM provider package not installed | error=%s", str(e))
        raise

    except ValueError as e:
        logger.error("LLM configuration error | error=%s", str(e))
        raise

    except Exception as e:
        logger.error("LLM call failed | provider=%s | error=%s", provider, str(e))
        raise


def generate(parsed_files: list[ParsedFile]) -> list[ReviewFinding]:

    all_findings = []

    system_prompt = _build_system_prompt()

    for parsed_file in parsed_files:
        # Skip files with syntax errors - we can't analyze them properly
        if parsed_file.syntax_errors:
            logger.info(
                "Skipping file with syntax errors | filename=%s | errors=%s",
                parsed_file.filename,
                len(parsed_file.syntax_errors),
            )

            # Add a finding about the syntax error
            syntax_finding = ReviewFinding(
                filename=parsed_file.filename,
                line_number=1,
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                title="Syntax error in file",
                description=f"File contains syntax errors: {'; '.join(parsed_file.syntax_errors)}",
                suggestion="Fix the syntax errors before code can be analyzed.",
            )
            all_findings.append(syntax_finding)
            continue

        # Build file-specific context
        file_context = _build_file_context(parsed_file)

        # Construct complete prompt
        full_prompt = f"{system_prompt}\n\n{file_context}"

        logger.info(
            "Calling LLM for review | filename=%s | entities=%s",
            parsed_file.filename,
            len(parsed_file.entities),
        )

        try:
            # Call LLM
            response_text = _call_llm(full_prompt)

            # Parse response
            findings = _parse_ai_response(response_text, parsed_file.filename)

            all_findings.extend(findings)

            logger.info(
                "LLM review completed | filename=%s | findings=%s",
                parsed_file.filename,
                len(findings),
            )

        except Exception as e:
            logger.error(
                "LLM call failed | filename=%s | error=%s",
                parsed_file.filename,
                str(e),
            )
            # Continue with other files

    logger.info(
        "Review generation completed | total_files=%s | total_findings=%s",
        len(parsed_files),
        len(all_findings),
    )

    return all_findings
