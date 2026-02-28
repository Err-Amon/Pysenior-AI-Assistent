import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services import ai_review
from app.services.code_parser import ParsedFile, CodeEntity
from app.models.review_models import Category, ReviewFinding, Severity


class TestBuildSystemPrompt:
    def test_returns_string(self):
        prompt = ai_review._build_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 100

    def test_includes_review_categories(self):
        prompt = ai_review._build_system_prompt()

        assert "reliability" in prompt.lower()
        assert "security" in prompt.lower()
        assert "performance" in prompt.lower()
        assert "maintainability" in prompt.lower()

    def test_includes_severity_levels(self):
        prompt = ai_review._build_system_prompt()

        assert "low" in prompt.lower()
        assert "medium" in prompt.lower()
        assert "high" in prompt.lower()
        assert "critical" in prompt.lower()

    def test_includes_json_format_instruction(self):
        prompt = ai_review._build_system_prompt()

        assert "json" in prompt.lower()
        assert "array" in prompt.lower()


class TestBuildFileContext:
    def test_includes_filename(self):
        parsed_file = ParsedFile(
            filename="test.py",
            entities=[],
            raw_content="print('hello')",
            total_lines=1,
            imports=[],
            has_main_guard=False,
            syntax_errors=[],
        )

        context = ai_review._build_file_context(parsed_file)

        assert "test.py" in context

    def test_includes_line_count(self):
        parsed_file = ParsedFile(
            filename="test.py",
            entities=[],
            raw_content="line1\nline2\nline3",
            total_lines=3,
            imports=[],
            has_main_guard=False,
            syntax_errors=[],
        )

        context = ai_review._build_file_context(parsed_file)

        assert "3" in context

    def test_includes_imports(self):
        parsed_file = ParsedFile(
            filename="test.py",
            entities=[],
            raw_content="import os\nimport sys",
            total_lines=2,
            imports=["os", "sys", "json"],
            has_main_guard=False,
            syntax_errors=[],
        )

        context = ai_review._build_file_context(parsed_file)

        assert "os" in context
        assert "sys" in context

    def test_includes_entities(self):
        entity = CodeEntity(
            entity_type="function",
            name="test_function",
            line_start=5,
            line_end=10,
            complexity=3,
        )

        parsed_file = ParsedFile(
            filename="test.py",
            entities=[entity],
            raw_content="def test_function(): pass",
            total_lines=1,
            imports=[],
            has_main_guard=False,
            syntax_errors=[],
        )

        context = ai_review._build_file_context(parsed_file)

        assert "test_function" in context
        assert "5" in context
        assert "10" in context
        assert "complexity: 3" in context

    def test_includes_full_code(self):
        code = "def hello():\n    print('world')\n    return True"

        parsed_file = ParsedFile(
            filename="test.py",
            entities=[],
            raw_content=code,
            total_lines=3,
            imports=[],
            has_main_guard=False,
            syntax_errors=[],
        )

        context = ai_review._build_file_context(parsed_file)

        assert "print('world')" in context
        assert "def hello():" in context

    def test_truncates_long_docstrings(self):
        entity = CodeEntity(
            entity_type="function",
            name="test",
            line_start=1,
            line_end=5,
            docstring="A" * 150,  # 150 character docstring
        )

        parsed_file = ParsedFile(
            filename="test.py",
            entities=[entity],
            raw_content="def test(): pass",
            total_lines=1,
            imports=[],
            has_main_guard=False,
            syntax_errors=[],
        )

        context = ai_review._build_file_context(parsed_file)

        # Should be truncated with ...
        assert "..." in context


class TestParseAIResponse:
    def test_parses_valid_json_response(self):
        response = """[
            {
                "filename": "test.py",
                "line_number": 42,
                "severity": "high",
                "category": "security",
                "title": "SQL Injection Risk",
                "description": "Unsafe query",
                "suggestion": "Use parameterized queries"
            }
        ]"""

        findings = ai_review._parse_ai_response(response, "test.py")

        assert len(findings) == 1
        assert findings[0].filename == "test.py"
        assert findings[0].line_number == 42
        assert findings[0].severity == Severity.HIGH
        assert findings[0].category == Category.SECURITY

    def test_handles_markdown_wrapped_json(self):
        response = """```json
        [
            {
                "filename": "test.py",
                "line_number": 10,
                "severity": "medium",
                "category": "performance",
                "title": "Inefficient loop",
                "description": "O(n²) complexity",
                "suggestion": "Use set for lookups"
            }
        ]
        ```"""

        findings = ai_review._parse_ai_response(response, "test.py")

        assert len(findings) == 1
        assert findings[0].severity == Severity.MEDIUM

    def test_handles_plain_code_blocks(self):
        response = """```
        [{"filename": "test.py", "line_number": 5, "severity": "low", 
          "category": "maintainability", "title": "Test", 
          "description": "Desc", "suggestion": "Fix"}]
        ```"""

        findings = ai_review._parse_ai_response(response, "test.py")

        assert len(findings) == 1

    def test_returns_empty_for_invalid_json(self):
        response = "This is not JSON at all"

        findings = ai_review._parse_ai_response(response, "test.py")

        assert findings == []

    def test_skips_malformed_findings(self):
        response = """[
            {
                "filename": "test.py",
                "line_number": 10,
                "severity": "high",
                "category": "security",
                "title": "Good finding",
                "description": "Complete",
                "suggestion": "Fix it"
            },
            {
                "filename": "test.py",
                "line_number": 20,
                "severity": "high"
            }
        ]"""

        findings = ai_review._parse_ai_response(response, "test.py")

        # Should only get the valid one
        assert len(findings) == 1
        assert findings[0].line_number == 10

    def test_handles_empty_array(self):
        response = "[]"

        findings = ai_review._parse_ai_response(response, "test.py")

        assert findings == []

    def test_handles_non_list_response(self):
        response = '{"error": "not a list"}'

        findings = ai_review._parse_ai_response(response, "test.py")

        assert findings == []

    def test_uses_default_filename(self):
        response = """[{
            "line_number": 10,
            "severity": "low",
            "category": "style",
            "title": "Test",
            "description": "Desc",
            "suggestion": "Fix"
        }]"""

        findings = ai_review._parse_ai_response(response, "default.py")

        assert len(findings) == 1
        assert findings[0].filename == "default.py"


class TestCallLLMOpenAI:
    @patch("app.services.ai_review.openai.OpenAI")
    @patch("app.services.ai_review.get_settings")
    def test_calls_openai_api(self, mock_settings, mock_openai_class):
        """Should call OpenAI API with correct parameters."""
        # Setup mocks
        settings = Mock()
        settings.OPENAI_API_KEY = "sk-test123"
        mock_settings.return_value = settings

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"result": "test"}'))]
        mock_response.usage = Mock(total_tokens=100)
        mock_client.chat.completions.create.return_value = mock_response

        # Call function
        result = ai_review._call_llm_openai("system prompt", "user prompt")

        # Verify
        mock_openai_class.assert_called_once_with(api_key="sk-test123")
        mock_client.chat.completions.create.assert_called_once()
        assert result == '{"result": "test"}'

    @patch("app.services.ai_review.get_settings")
    def test_raises_error_without_api_key(self, mock_settings):
        settings = Mock()
        settings.OPENAI_API_KEY = None
        mock_settings.return_value = settings

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            ai_review._call_llm_openai("system", "user")

    @patch("app.services.ai_review.openai.OpenAI")
    @patch("app.services.ai_review.get_settings")
    @patch("app.services.ai_review.time.sleep")
    def test_retries_on_rate_limit(self, mock_sleep, mock_settings, mock_openai_class):
        """Should retry on rate limit error."""
        import openai

        settings = Mock()
        settings.OPENAI_API_KEY = "sk-test"
        mock_settings.return_value = settings

        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[]"))]
        mock_response.usage = Mock(total_tokens=50)

        mock_client.chat.completions.create.side_effect = [
            openai.RateLimitError("Rate limit", response=Mock(), body=None),
            mock_response,
        ]

        result = ai_review._call_llm_openai("system", "user")

        # Should have retried
        assert mock_client.chat.completions.create.call_count == 2
        assert result == "[]"


class TestCallLLMGemini:
    @patch("app.services.ai_review.genai")
    @patch("app.services.ai_review.get_settings")
    def test_calls_gemini_api(self, mock_settings, mock_genai):
        settings = Mock()
        settings.GEMINI_API_KEY = "AIzaSy-test"
        mock_settings.return_value = settings

        mock_model = Mock()
        mock_response = Mock(text='[{"test": "result"}]')
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        result = ai_review._call_llm_gemini("system prompt", "user prompt")

        mock_genai.configure.assert_called_once_with(api_key="AIzaSy-test")
        assert result == '[{"test": "result"}]'

    @patch("app.services.ai_review.get_settings")
    def test_raises_error_without_gemini_key(self, mock_settings):
        settings = Mock()
        settings.GEMINI_API_KEY = None
        mock_settings.return_value = settings

        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            ai_review._call_llm_gemini("system", "user")


class TestGenerate:
    @patch("app.services.ai_review._call_llm")
    def test_processes_parsed_files(self, mock_call_llm):
        mock_call_llm.return_value = "[]"

        parsed_files = [
            ParsedFile(
                filename="file1.py",
                entities=[],
                raw_content="code1",
                total_lines=10,
                imports=[],
                has_main_guard=False,
                syntax_errors=[],
            ),
            ParsedFile(
                filename="file2.py",
                entities=[],
                raw_content="code2",
                total_lines=20,
                imports=[],
                has_main_guard=False,
                syntax_errors=[],
            ),
        ]

        findings = ai_review.generate(parsed_files)

        # Should call LLM twice (once per file)
        assert mock_call_llm.call_count == 2
        assert isinstance(findings, list)

    @patch("app.services.ai_review._call_llm")
    def test_skips_files_with_syntax_errors(self, mock_call_llm):
        parsed_file = ParsedFile(
            filename="broken.py",
            entities=[],
            raw_content="def broken(",
            total_lines=1,
            imports=[],
            has_main_guard=False,
            syntax_errors=["Syntax error on line 1"],
        )

        findings = ai_review.generate([parsed_file])

        # Should not call LLM
        assert mock_call_llm.call_count == 0

        # Should have syntax error finding
        assert len(findings) == 1
        assert findings[0].severity == Severity.CRITICAL
        assert "syntax error" in findings[0].title.lower()

    @patch("app.services.ai_review._call_llm")
    def test_aggregates_findings_from_multiple_files(self, mock_call_llm):
        mock_call_llm.side_effect = [
            '[{"filename": "f1.py", "line_number": 1, "severity": "high", '
            '"category": "security", "title": "T1", "description": "D1", "suggestion": "S1"}]',
            '[{"filename": "f2.py", "line_number": 2, "severity": "medium", '
            '"category": "performance", "title": "T2", "description": "D2", "suggestion": "S2"}]',
        ]

        parsed_files = [
            ParsedFile("f1.py", [], "code", 1, [], False, []),
            ParsedFile("f2.py", [], "code", 1, [], False, []),
        ]

        findings = ai_review.generate(parsed_files)

        assert len(findings) == 2
        assert findings[0].filename == "f1.py"
        assert findings[1].filename == "f2.py"

    @patch("app.services.ai_review._call_llm")
    def test_continues_on_llm_failure(self, mock_call_llm):
        mock_call_llm.side_effect = [
            Exception("LLM error"),
            '[{"filename": "f2.py", "line_number": 1, "severity": "low", '
            '"category": "style", "title": "T", "description": "D", "suggestion": "S"}]',
        ]

        parsed_files = [
            ParsedFile("f1.py", [], "code", 1, [], False, []),
            ParsedFile("f2.py", [], "code", 1, [], False, []),
        ]

        findings = ai_review.generate(parsed_files)

        # Should have finding from second file
        assert len(findings) == 1
        assert findings[0].filename == "f2.py"

    @patch("app.services.ai_review._call_llm")
    def test_returns_empty_list_for_no_files(self, mock_call_llm):
        findings = ai_review.generate([])

        assert findings == []
        assert mock_call_llm.call_count == 0


class TestLLMProviderRouting:
    @patch("app.services.ai_review._call_llm_openai")
    @patch("app.services.ai_review.get_settings")
    def test_routes_to_openai(self, mock_settings, mock_openai):
        settings = Mock()
        settings.LLM_PROVIDER = "openai"
        mock_settings.return_value = settings
        mock_openai.return_value = "result"

        result = ai_review._call_llm("system\n\nuser")

        mock_openai.assert_called_once()
        assert result == "result"

    @patch("app.services.ai_review._call_llm_gemini")
    @patch("app.services.ai_review.get_settings")
    def test_routes_to_gemini(self, mock_settings, mock_gemini):
        settings = Mock()
        settings.LLM_PROVIDER = "gemini"
        mock_settings.return_value = settings
        mock_gemini.return_value = "result"

        result = ai_review._call_llm("system\n\nuser")

        mock_gemini.assert_called_once()
        assert result == "result"

    @patch("app.services.ai_review.get_settings")
    def test_raises_error_for_invalid_provider(self, mock_settings):
        settings = Mock()
        settings.LLM_PROVIDER = "invalid_provider"
        mock_settings.return_value = settings

        with pytest.raises(ValueError, match="Invalid LLM provider"):
            ai_review._call_llm("system\n\nuser")
