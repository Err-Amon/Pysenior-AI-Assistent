import pytest

from app.models.review_models import Category, ReviewFinding, Severity
from app.services import scoring


class TestCategoryScoreCalculation:
    def test_perfect_score_with_no_findings(self):
        findings = []

        result = scoring._calculate_category_score(findings, Category.SECURITY)

        assert result.score == 100
        assert result.issue_count == 0
        assert result.deductions == 0

    def test_deducts_points_for_low_severity(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.LOW,
                category=Category.SECURITY,
                title="Minor issue",
                description="This is a minor security concern",
                suggestion="Consider fixing this",
            )
        ]

        result = scoring._calculate_category_score(findings, Category.SECURITY)

        assert result.score == 98  # 100 - 2
        assert result.issue_count == 1
        assert result.deductions == 2

    def test_deducts_points_for_medium_severity(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.MEDIUM,
                category=Category.PERFORMANCE,
                title="Inefficient loop",
                description="This loop is inefficient",
                suggestion="Use list comprehension",
            )
        ]

        result = scoring._calculate_category_score(findings, Category.PERFORMANCE)

        assert result.score == 95  # 100 - 5

    def test_deducts_points_for_high_severity(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="Missing error handling",
                description="No exception handling",
                suggestion="Add try-except",
            )
        ]

        result = scoring._calculate_category_score(findings, Category.RELIABILITY)

        assert result.score == 90  # 100 - 10

    def test_deducts_points_for_critical_severity(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="SQL Injection",
                description="Unsafe SQL query",
                suggestion="Use parameterized queries",
            )
        ]

        result = scoring._calculate_category_score(findings, Category.SECURITY)

        assert result.score == 80  # 100 - 20

    def test_accumulates_multiple_deductions(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Issue 1",
                description="Critical issue",
                suggestion="Fix this",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.HIGH,
                category=Category.SECURITY,
                title="Issue 2",
                description="High severity issue",
                suggestion="Fix this too",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=30,
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                title="Issue 3",
                description="Medium issue",
                suggestion="Consider fixing",
            ),
        ]

        result = scoring._calculate_category_score(findings, Category.SECURITY)

        # 100 - 20 (critical) - 10 (high) - 5 (medium) = 65
        assert result.score == 65
        assert result.issue_count == 3
        assert result.deductions == 35

    def test_ignores_findings_from_other_categories(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.SECURITY,
                title="Security issue",
                description="Security problem",
                suggestion="Fix security",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.HIGH,
                category=Category.PERFORMANCE,
                title="Performance issue",
                description="Slow code",
                suggestion="Optimize",
            ),
        ]

        result = scoring._calculate_category_score(findings, Category.SECURITY)

        # Should only deduct for security finding
        assert result.score == 90  # 100 - 10
        assert result.issue_count == 1

    def test_floors_score_at_zero(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=i,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title=f"Issue {i}",
                description="Critical issue",
                suggestion="Fix",
            )
            for i in range(10)  # 10 critical issues = 200 points deducted
        ]

        result = scoring._calculate_category_score(findings, Category.SECURITY)

        assert result.score == 0  # Floored at 0, not -100


class TestOverallScoreCalculation:
    def test_calculates_weighted_average(self):
        category_scores = {
            Category.RELIABILITY: 90,
            Category.SECURITY: 80,
            Category.PERFORMANCE: 70,
            Category.MAINTAINABILITY: 60,
        }

        result = scoring._calculate_overall_score(category_scores)

        # (90 * 0.30) + (80 * 0.35) + (70 * 0.20) + (60 * 0.15)
        # = 27 + 28 + 14 + 9 = 78
        assert result == 78

    def test_security_weighted_highest(self):
        # Perfect scores except security
        high_security = {
            Category.RELIABILITY: 100,
            Category.SECURITY: 100,
            Category.PERFORMANCE: 100,
            Category.MAINTAINABILITY: 100,
        }

        low_security = {
            Category.RELIABILITY: 100,
            Category.SECURITY: 50,
            Category.PERFORMANCE: 100,
            Category.MAINTAINABILITY: 100,
        }

        score_high = scoring._calculate_overall_score(high_security)
        score_low = scoring._calculate_overall_score(low_security)

        # Security is 35% weight, so 50 point drop = 17.5 point impact
        assert score_high == 100
        assert score_low == 82  # 100 - 18 (rounded)

    def test_floors_at_zero(self):
        category_scores = {
            Category.RELIABILITY: 0,
            Category.SECURITY: 0,
            Category.PERFORMANCE: 0,
            Category.MAINTAINABILITY: 0,
        }

        result = scoring._calculate_overall_score(category_scores)

        assert result == 0

    def test_ceiling_at_100(self):
        category_scores = {
            Category.RELIABILITY: 100,
            Category.SECURITY: 100,
            Category.PERFORMANCE: 100,
            Category.MAINTAINABILITY: 100,
        }

        result = scoring._calculate_overall_score(category_scores)

        assert result == 100


class TestSeverityCount:
    def test_counts_findings_by_severity(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Critical",
                description="Critical issue",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Critical 2",
                description="Another critical",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=30,
                severity=Severity.HIGH,
                category=Category.PERFORMANCE,
                title="High",
                description="High issue",
                suggestion="Fix",
            ),
        ]

        result = scoring._count_by_severity(findings)

        assert result[Severity.CRITICAL] == 2
        assert result[Severity.HIGH] == 1


class TestCalculateScoreCard:
    def test_returns_perfect_scores_for_no_findings(self):
        findings = []

        scorecard = scoring.calculate(findings)

        assert scorecard.reliability == 100
        assert scorecard.security == 100
        assert scorecard.performance == 100
        assert scorecard.maintainability == 100
        assert scorecard.overall == 100
        assert scorecard.total_findings == 0
        assert scorecard.critical_count == 0
        assert scorecard.high_count == 0

    def test_calculates_all_category_scores(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="Reliability issue",
                description="Missing error handling",
                suggestion="Add try-except",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Security issue",
                description="SQL injection risk",
                suggestion="Use parameterized queries",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=30,
                severity=Severity.MEDIUM,
                category=Category.PERFORMANCE,
                title="Performance issue",
                description="Inefficient loop",
                suggestion="Optimize",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=40,
                severity=Severity.LOW,
                category=Category.MAINTAINABILITY,
                title="Maintainability issue",
                description="Missing docstring",
                suggestion="Add documentation",
            ),
        ]

        scorecard = scoring.calculate(findings)

        assert scorecard.reliability == 90  # 100 - 10 (high)
        assert scorecard.security == 80  # 100 - 20 (critical)
        assert scorecard.performance == 95  # 100 - 5 (medium)
        assert scorecard.maintainability == 98  # 100 - 2 (low)

    def test_calculates_weighted_overall_score(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Critical security",
                description="Bad",
                suggestion="Fix",
            ),
        ]

        scorecard = scoring.calculate(findings)

        # Security: 80 (100 - 20)
        # Others: 100
        # (80 * 0.35) + (100 * 0.30) + (100 * 0.20) + (100 * 0.15)
        # = 28 + 30 + 20 + 15 = 93
        assert scorecard.overall == 93

    def test_includes_detailed_breakdowns(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.SECURITY,
                title="Issue",
                description="Problem",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.MEDIUM,
                category=Category.SECURITY,
                title="Issue 2",
                description="Problem 2",
                suggestion="Fix 2",
            ),
        ]

        scorecard = scoring.calculate(findings)

        assert scorecard.security_details is not None
        assert scorecard.security_details.issue_count == 2
        assert scorecard.security_details.deductions == 15  # 10 + 5

    def test_counts_critical_and_high_severity(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="Critical 1",
                description="Bad",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=20,
                severity=Severity.CRITICAL,
                category=Category.RELIABILITY,
                title="Critical 2",
                description="Bad",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=30,
                severity=Severity.HIGH,
                category=Category.PERFORMANCE,
                title="High 1",
                description="Issue",
                suggestion="Fix",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=40,
                severity=Severity.MEDIUM,
                category=Category.MAINTAINABILITY,
                title="Medium 1",
                description="Issue",
                suggestion="Fix",
            ),
        ]

        scorecard = scoring.calculate(findings)

        assert scorecard.total_findings == 4
        assert scorecard.critical_count == 2
        assert scorecard.high_count == 1


class TestRealisticScenarios:
    def test_mostly_minor_issues(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=i,
                severity=Severity.LOW,
                category=Category.MAINTAINABILITY,
                title=f"Minor issue {i}",
                description="Small problem",
                suggestion="Easy fix",
            )
            for i in range(5)  # 5 low severity issues
        ]

        scorecard = scoring.calculate(findings)

        # 5 * 2 = 10 points deducted from maintainability
        assert scorecard.maintainability == 90
        # Overall should still be high since maintainability is only 15% weight
        assert scorecard.overall >= 98

    def test_critical_security_vulnerability(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.CRITICAL,
                category=Category.SECURITY,
                title="SQL Injection",
                description="Direct SQL concatenation",
                suggestion="Use parameterized queries",
            ),
        ]

        scorecard = scoring.calculate(findings)

        assert scorecard.security == 80
        # Security is 35% weight, so overall = (80 * 0.35) + (100 * 0.65) = 93
        assert scorecard.overall == 93

    def test_multiple_high_severity_reliability_issues(self):
        findings = [
            ReviewFinding(
                filename="test.py",
                line_number=10,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="No error handling",
                description="Missing try-except",
                suggestion="Add error handling",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=30,
                severity=Severity.HIGH,
                category=Category.RELIABILITY,
                title="Unchecked None",
                description="No None check",
                suggestion="Add validation",
            ),
            ReviewFinding(
                filename="test.py",
                line_number=50,
                severity=Severity.MEDIUM,
                category=Category.RELIABILITY,
                title="Weak validation",
                description="Insufficient input validation",
                suggestion="Strengthen validation",
            ),
        ]

        scorecard = scoring.calculate(findings)

        # 10 + 10 + 5 = 25 points deducted
        assert scorecard.reliability == 75
