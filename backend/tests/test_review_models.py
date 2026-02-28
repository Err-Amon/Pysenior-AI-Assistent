import pytest
from pydantic import ValidationError

from app.models.review_models import (
    Category,
    Severity,
    ReviewIssue,
    ReviewFinding,
    ReviewResult,
    AIReviewResult,
    FileReviewRequest,
    FileReviewResponse,
)


class TestSeverity:
    def test_severity_values(self):
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"

    def test_severity_from_string(self):
        assert Severity("low") == Severity.LOW
        assert Severity("critical") == Severity.CRITICAL


class TestCategory:
    def test_category_values(self):
        assert Category.RELIABILITY == "reliability"
        assert Category.SECURITY == "security"
        assert Category.PERFORMANCE == "performance"
        assert Category.MAINTAINABILITY == "maintainability"
        assert Category.STYLE == "style"

    def test_category_from_string(self):
        assert Category("security") == Category.SECURITY
        assert Category("performance") == Category.PERFORMANCE


class TestReviewIssue:
    def test_create_review_issue(self):
        issue = ReviewIssue(
            line=42,
            issue="Variable name is unclear",
            fix="Rename to 'user_count' for clarity",
        )

        assert issue.line == 42
        assert issue.issue == "Variable name is unclear"
        assert issue.fix == "Rename to 'user_count' for clarity"

    def test_review_issue_line_optional(self):
        """Should allow None for line number."""
        issue = ReviewIssue(
            line=None,
            issue="General code structure issue",
            fix="Refactor into smaller functions",
        )

        assert issue.line is None

    def test_review_issue_without_line(self):
        """Should work without line number."""
        issue = ReviewIssue(issue="Missing error handling", fix="Add try-except blocks")

        assert issue.line is None


class TestReviewFinding:
    def test_create_valid_review_finding(self):
        finding = ReviewFinding(
            filename="auth.py",
            line_number=42,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="SQL Injection Risk",
            description="Direct string concatenation in SQL query creates injection vulnerability",
            suggestion="Use parameterized queries with placeholders",
        )

        assert finding.filename == "auth.py"
        assert finding.line_number == 42
        assert finding.severity == Severity.HIGH
        assert finding.category == Category.SECURITY
        assert finding.title == "SQL Injection Risk"

    def test_review_finding_with_code_snippet(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=10,
            severity=Severity.MEDIUM,
            category=Category.MAINTAINABILITY,
            title="Complex function",
            description="Function is too complex",
            suggestion="Break into smaller functions",
            code_snippet="def complex_function():\n    # 100 lines...",
        )

        assert finding.code_snippet is not None
        assert "complex_function" in finding.code_snippet

    def test_review_finding_to_review_issue(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=42,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="Security Issue",
            description="Unsafe operation",
            suggestion="Use safe alternative",
        )

        issue = finding.to_review_issue()

        assert isinstance(issue, ReviewIssue)
        assert issue.line == 42
        assert "Security Issue" in issue.issue
        assert "Unsafe operation" in issue.issue
        assert issue.fix == "Use safe alternative"

    def test_review_finding_requires_all_fields(self):
        with pytest.raises(ValidationError):
            ReviewFinding(
                filename="test.py",
                line_number=42,
                # Missing severity, category, title, description, suggestion
            )


class TestReviewResult:
    def test_create_empty_review_result(self):
        result = ReviewResult()

        assert result.findings == []
        assert result.summary is None
        assert result.files_analyzed == 0
        assert result.total_issues == 0

    def test_review_result_with_findings(self):
        finding1 = ReviewFinding(
            filename="file1.py",
            line_number=10,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="Issue 1",
            description="Desc 1",
            suggestion="Fix 1",
        )

        finding2 = ReviewFinding(
            filename="file2.py",
            line_number=20,
            severity=Severity.MEDIUM,
            category=Category.PERFORMANCE,
            title="Issue 2",
            description="Desc 2",
            suggestion="Fix 2",
        )

        result = ReviewResult(
            findings=[finding1, finding2],
            summary="Review completed with 2 issues",
            files_analyzed=2,
            total_issues=2,
        )

        assert len(result.findings) == 2
        assert result.files_analyzed == 2
        assert result.total_issues == 2

    def test_review_result_with_summary(self):
        result = ReviewResult(summary="Overall code quality is good with minor issues")

        assert result.summary is not None


class TestAIReviewResult:
    def test_create_ai_review_result(self):
        result = AIReviewResult(
            summary="Good code with some improvements needed",
            praise=["Well-structured functions", "Good error handling"],
            critical_issues=[],
            warnings=[ReviewIssue(line=42, issue="Warning", fix="Fix it")],
            suggestions=[ReviewIssue(line=50, issue="Suggestion", fix="Consider this")],
            scores={
                "reliability": 8.5,
                "security": 7.0,
                "performance": 9.0,
                "maintainability": 8.0,
            },
        )

        assert result.summary == "Good code with some improvements needed"
        assert len(result.praise) == 2
        assert len(result.warnings) == 1
        assert len(result.suggestions) == 1

    def test_ai_review_result_default_scores(self):
        result = AIReviewResult(summary="Test")

        assert result.scores["reliability"] == 7.0
        assert result.scores["security"] == 7.0
        assert result.scores["performance"] == 7.0
        assert result.scores["maintainability"] == 7.0

    def test_ai_review_result_from_review_result(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Critical Issue",
                description="Bad",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="High Issue",
                description="Warning",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=30,
                severity=Severity.MEDIUM,
                category=Category.PERFORMANCE,
                title="Medium Issue",
                description="Suggestion",
                suggestion="Improve",
            ),
        ]

        review_result = ReviewResult(findings=findings, summary="Test review")

        scores = {
            "reliability": 8.0,
            "security": 7.5,
            "performance": 8.5,
            "maintainability": 9.0,
        }

        ai_result = AIReviewResult.from_review_result(review_result, scores)

        assert len(ai_result.critical_issues) == 1
        assert len(ai_result.warnings) == 1
        assert len(ai_result.suggestions) == 1
        assert ai_result.scores == scores

    def test_ai_review_result_empty_lists_default(self):
        result = AIReviewResult(summary="Test")

        assert result.praise == []
        assert result.critical_issues == []
        assert result.warnings == []
        assert result.suggestions == []


class TestFileReviewRequest:
    def test_create_file_review_request(self):
        request = FileReviewRequest(filename="auth.py", code="def login(user): pass")

        assert request.filename == "auth.py"
        assert request.code == "def login(user): pass"
        assert request.diff == ""
        assert request.ast_issues == []

    def test_file_review_request_with_diff(self):
        request = FileReviewRequest(
            filename="test.py", code="new code", diff="@@ -1,3 +1,3 @@"
        )

        assert request.diff == "@@ -1,3 +1,3 @@"

    def test_file_review_request_with_ast_issues(self):
        request = FileReviewRequest(
            filename="broken.py",
            code="def broken(",
            ast_issues=["Syntax error on line 1"],
        )

        assert len(request.ast_issues) == 1


class TestFileReviewResponse:
    def test_create_file_review_response(self):
        response = FileReviewResponse(
            filename="test.py",
            summary="Good code quality",
            grade="A",
            overall_score=9.0,
            critical_issues=[],
            warnings=[ReviewIssue(line=10, issue="Warning", fix="Fix")],
            suggestions=[],
            scores={
                "reliability": 9.0,
                "security": 8.5,
                "performance": 9.5,
                "maintainability": 8.0,
            },
        )

        assert response.filename == "test.py"
        assert response.grade == "A"
        assert response.overall_score == 9.0
        assert len(response.warnings) == 1

    def test_file_review_response_defaults(self):
        response = FileReviewResponse(
            filename="test.py", summary="Test", grade="B", overall_score=8.0
        )

        assert response.critical_issues == []
        assert response.warnings == []
        assert response.suggestions == []
        assert response.scores == {}


class TestModelConversions:
    def test_finding_to_issue_preserves_data(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=42,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="Security Risk",
            description="This is dangerous",
            suggestion="Do this instead",
        )

        issue = finding.to_review_issue()

        assert issue.line == finding.line_number
        assert finding.title in issue.issue
        assert finding.description in issue.issue
        assert issue.fix == finding.suggestion

    def test_multiple_findings_to_ai_result(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=i,
                severity=severity,
                category=Category.SECURITY,
                title=f"Issue {i}",
                description="Desc",
                suggestion="Fix",
            )
            for i, severity in enumerate(
                [
                    Severity.CRITICAL,
                    Severity.CRITICAL,
                    Severity.HIGH,
                    Severity.HIGH,
                    Severity.HIGH,
                    Severity.MEDIUM,
                    Severity.LOW,
                ]
            )
        ]

        review_result = ReviewResult(findings=findings)
        ai_result = AIReviewResult.from_review_result(review_result, {})

        assert len(ai_result.critical_issues) == 2
        assert len(ai_result.warnings) == 3  # HIGH severity
        assert len(ai_result.suggestions) == 2  # MEDIUM and LOW


class TestJSONSerialization:
    def test_review_finding_json_serialization(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=42,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="Test",
            description="Desc",
            suggestion="Fix",
        )

        json_data = finding.model_dump()

        assert json_data["filename"] == "test.py"
        assert json_data["severity"] == "high"
        assert json_data["category"] == "security"

    def test_ai_review_result_json_serialization(self):
        result = AIReviewResult(
            summary="Test", praise=["Good code"], scores={"reliability": 8.0}
        )

        json_data = result.model_dump()

        assert json_data["summary"] == "Test"
        assert len(json_data["praise"]) == 1
        assert json_data["scores"]["reliability"] == 8.0
