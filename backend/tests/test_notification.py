import pytest
import logging
from unittest.mock import Mock, patch

from app.models.review_models import Category, ReviewFinding, Severity
from app.models.score_models import CategoryScore, ScoreCard
from app.services import notification


class TestFormatScoreBadge:
    def test_excellent_score_gets_green_badge(self):
        assert notification._format_score_badge(100) == "🟢"
        assert notification._format_score_badge(95) == "🟢"
        assert notification._format_score_badge(90) == "🟢"

    def test_good_score_gets_yellow_badge(self):
        assert notification._format_score_badge(89) == "🟡"
        assert notification._format_score_badge(80) == "🟡"
        assert notification._format_score_badge(75) == "🟡"

    def test_fair_score_gets_orange_badge(self):
        assert notification._format_score_badge(74) == "🟠"
        assert notification._format_score_badge(65) == "🟠"
        assert notification._format_score_badge(60) == "🟠"

    def test_poor_score_gets_red_badge(self):
        assert notification._format_score_badge(59) == "🔴"
        assert notification._format_score_badge(30) == "🔴"
        assert notification._format_score_badge(0) == "🔴"


class TestFormatSeverityIcon:
    def test_returns_correct_icons_for_each_severity(self):
        assert notification._format_severity_icon(Severity.LOW) == "ℹ️"
        assert notification._format_severity_icon(Severity.MEDIUM) == "⚠️"
        assert notification._format_severity_icon(Severity.HIGH) == "🔴"
        assert notification._format_severity_icon(Severity.CRITICAL) == "🚨"


class TestBuildSummaryComment:
    def test_includes_overall_score(self):
        scorecard = ScoreCard(
            reliability=90,
            security=85,
            performance=88,
            maintainability=92,
            overall=88,
            total_findings=5,
            critical_count=1,
            high_count=2,
        )

        summary = notification._build_summary_comment(scorecard, [])

        assert "## PySenior Code Review" in summary
        assert "88/100" in summary
        assert "Overall Score" in summary

    def test_includes_score_breakdown_table(self):
        scorecard = ScoreCard(
            reliability=90,
            security=80,
            performance=85,
            maintainability=88,
            overall=85,
            reliability_details=CategoryScore(score=90, issue_count=2, deductions=10),
            security_details=CategoryScore(score=80, issue_count=3, deductions=20),
            performance_details=CategoryScore(score=85, issue_count=1, deductions=15),
            maintainability_details=CategoryScore(
                score=88, issue_count=0, deductions=12
            ),
            total_findings=6,
            critical_count=1,
            high_count=2,
        )

        summary = notification._build_summary_comment(scorecard, [])

        assert "Score Breakdown" in summary
        assert "| Category | Score | Issues |" in summary
        assert "Reliability" in summary
        assert "Security" in summary
        assert "Performance" in summary
        assert "Maintainability" in summary
        assert "90/100" in summary
        assert "80/100" in summary

    def test_includes_issue_summary_when_findings_exist(self):
        scorecard = ScoreCard(
            reliability=90,
            security=80,
            performance=85,
            maintainability=88,
            overall=85,
            total_findings=10,
            critical_count=2,
            high_count=5,
        )

        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="SQL Injection",
                description="Unsafe SQL",
                suggestion="Fix it",
            )
        ]

        summary = notification._build_summary_comment(scorecard, findings)

        assert "Issue Summary" in summary
        assert "Total Issues:" in summary
        assert "Critical:" in summary
        assert "High:" in summary

    def test_lists_critical_issues(self):
        scorecard = ScoreCard(
            reliability=80,
            security=60,
            performance=85,
            maintainability=88,
            overall=75,
            total_findings=3,
            critical_count=2,
            high_count=1,
        )

        findings = [
            ReviewFinding(
                filename="auth.py",
                line_number=42,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Hardcoded password",
                description="Password in source",
                suggestion="Use env vars",
            ),
            ReviewFinding(
                filename="db.py",
                line_number=100,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="SQL Injection",
                description="Unsafe query",
                suggestion="Use params",
            ),
        ]

        summary = notification._build_summary_comment(scorecard, findings)

        assert "Critical Issues" in summary
        assert "auth.py:42" in summary
        assert "Hardcoded password" in summary
        assert "db.py:100" in summary
        assert "SQL Injection" in summary

    def test_limits_critical_issues_in_summary(self):
        scorecard = ScoreCard(
            reliability=50,
            security=40,
            performance=85,
            maintainability=88,
            overall=60,
            total_findings=10,
            critical_count=7,
            high_count=3,
        )

        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=i,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title=f"Critical issue {i}",
                description="Problem",
                suggestion="Fix",
            )
            for i in range(7)
        ]

        summary = notification._build_summary_comment(scorecard, findings)

        # Should show "2 more critical issues..."
        assert "2 more critical issues" in summary

    def test_shows_success_message_for_no_issues(self):
        scorecard = ScoreCard(
            reliability=100,
            security=100,
            performance=100,
            maintainability=100,
            overall=100,
            total_findings=0,
            critical_count=0,
            high_count=0,
        )

        summary = notification._build_summary_comment(scorecard, [])

        assert "Great work! No issues found" in summary

    def test_includes_footer(self):
        scorecard = ScoreCard(
            reliability=90,
            security=90,
            performance=90,
            maintainability=90,
            overall=90,
            total_findings=0,
            critical_count=0,
            high_count=0,
        )

        summary = notification._build_summary_comment(scorecard, [])

        assert "PySenior" in summary
        assert "AI Senior Python Engineer" in summary


class TestBuildInlineComment:
    def test_includes_severity_and_category(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=42,
            severity=Severity.HIGH,
            category=Category.SECURITY,
            title="Unsafe operation",
            description="This is unsafe",
            suggestion="Make it safe",
        )

        comment = notification._build_inline_comment(finding)

        assert "HIGH" in comment
        assert "Security" in comment

    def test_includes_title_description_suggestion(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=42,
            severity=Severity.MEDIUM,
            category=Category.PERFORMANCE,
            title="Inefficient loop",
            description="This loop is O(n²) when it could be O(n)",
            suggestion="Use a set for faster lookups",
        )

        comment = notification._build_inline_comment(finding)

        assert "Inefficient loop" in comment
        assert "This loop is O(n²)" in comment
        assert "Use a set for faster lookups" in comment
        assert "Issue:" in comment
        assert "Suggestion:" in comment

    def test_includes_code_snippet_when_present(self):
        finding = ReviewFinding(
            filename="test.py",
            line_number=42,
            severity=Severity.CRITICAL,
            category=Category.SECURITY,
            title="Shell injection",
            description="Using shell=True",
            suggestion="Use list arguments",
            code_snippet='subprocess.run(f"rm {user_input}", shell=True)',
        )

        comment = notification._build_inline_comment(finding)

        assert "```python" in comment
        assert "subprocess.run" in comment
        assert "shell=True" in comment


class TestGroupFindingsByFile:
    def test_groups_findings_by_filename(self):
        findings = [
            ReviewFinding(
                filename="file1.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.SECURITY,
                title="Issue 1",
                description="Problem 1",
                suggestion="Fix 1",
            ),
            ReviewFinding(
                filename="file1.py",
                line_number=20,
                severity=Severity.MEDIUM,
                category=Category.PERFORMANCE,
                title="Issue 2",
                description="Problem 2",
                suggestion="Fix 2",
            ),
            ReviewFinding(
                filename="file2.py",
                line_number=5,
                severity=Severity.LOW,
                category=Category.MAINTAINABILITY,
                title="Issue 3",
                description="Problem 3",
                suggestion="Fix 3",
            ),
        ]

        grouped = notification._group_findings_by_file(findings)

        assert "file1.py" in grouped
        assert "file2.py" in grouped
        assert len(grouped["file1.py"]) == 2
        assert len(grouped["file2.py"]) == 1


class TestPost:
    @patch("app.services.notification.github_service")
    def test_posts_summary_comment(self, mock_github):
        scorecard = ScoreCard(
            reliability=90,
            security=85,
            performance=88,
            maintainability=92,
            overall=88,
            total_findings=0,
            critical_count=0,
            high_count=0,
        )

        notification.post("owner/repo", 42, [], scorecard)

        mock_github.post_issue_comment.assert_called_once()
        call_args = mock_github.post_issue_comment.call_args
        assert call_args[0][0] == "owner/repo"
        assert call_args[0][1] == 42
        # Verify comment contains key information
        comment = call_args[0][2]
        assert "88/100" in comment
        assert "PySenior" in comment

    @patch("app.services.notification.github_service")
    def test_posts_inline_comments_for_each_finding(self, mock_github):
        scorecard = ScoreCard(
            reliability=80,
            security=70,
            performance=85,
            maintainability=88,
            overall=80,
            total_findings=2,
            critical_count=1,
            high_count=1,
        )

        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Issue 1",
                description="Problem 1",
                suggestion="Fix 1",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="Issue 2",
                description="Problem 2",
                suggestion="Fix 2",
            ),
        ]

        notification.post("owner/repo", 42, findings, scorecard)

        # Should post 1 summary + 2 inline comments
        assert mock_github.post_issue_comment.call_count == 1
        assert mock_github.post_review_comment.call_count == 2

    @patch("app.services.notification.github_service")
    def test_continues_on_inline_comment_failure(self, mock_github, caplog):
        scorecard = ScoreCard(
            reliability=80,
            security=70,
            performance=85,
            maintainability=88,
            overall=80,
            total_findings=2,
            critical_count=0,
            high_count=2,
        )

        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.SECURITY,
                title="Issue 1",
                description="Problem 1",
                suggestion="Fix 1",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="Issue 2",
                description="Problem 2",
                suggestion="Fix 2",
            ),
        ]

        # Make first inline comment fail
        mock_github.post_review_comment.side_effect = [
            Exception("Line not in diff"),
            None,  # Second call succeeds
        ]

        notification.post("owner/repo", 42, findings, scorecard)

        # Should still attempt both inline comments
        assert mock_github.post_review_comment.call_count == 2
        # Should log the failure
        assert "Failed to post inline comment" in caplog.text

    @patch("app.services.notification.github_service")
    def test_raises_exception_if_summary_fails(self, mock_github):
        scorecard = ScoreCard(
            reliability=90,
            security=85,
            performance=88,
            maintainability=92,
            overall=88,
            total_findings=0,
            critical_count=0,
            high_count=0,
        )

        mock_github.post_issue_comment.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            notification.post("owner/repo", 42, [], scorecard)

    @patch("app.services.notification.github_service")
    def test_logs_completion_statistics(self, mock_github, caplog):
        caplog.set_level(logging.INFO)
        scorecard = ScoreCard(
            reliability=80,
            security=70,
            performance=85,
            maintainability=88,
            overall=80,
            total_findings=3,
            critical_count=1,
            high_count=2,
        )

        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=i,
                severity=Severity.HIGH,
                category=Category.SECURITY,
                title=f"Issue {i}",
                description="Problem",
                suggestion="Fix",
            )
            for i in range(3)
        ]

        # Make 1 comment fail
        mock_github.post_review_comment.side_effect = [
            None,
            Exception("Failed"),
            None,
        ]

        notification.post("owner/repo", 42, findings, scorecard)

        assert "Review posting completed" in caplog.text
        assert "posted=2" in caplog.text
        assert "failed=1" in caplog.text
