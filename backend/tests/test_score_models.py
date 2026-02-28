import pytest
from pydantic import ValidationError

from app.models.score_models import (
    ScoreBreakdown,
    CategoryScore,
    ScoreCard,
    CodeScore,
    FileReview,
)


class TestScoreBreakdown:
    def test_create_score_breakdown(self):
        breakdown = ScoreBreakdown(
            score=8.5,
            issues=["Issue 1", "Issue 2"],
            suggestions=["Try this", "Consider that"],
        )

        assert breakdown.score == 8.5
        assert len(breakdown.issues) == 2
        assert len(breakdown.suggestions) == 2

    def test_score_breakdown_defaults(self):
        breakdown = ScoreBreakdown(score=9.0)

        assert breakdown.issues == []
        assert breakdown.suggestions == []

    def test_score_breakdown_validates_range(self):
        # Valid scores
        ScoreBreakdown(score=0.0)
        ScoreBreakdown(score=5.5)
        ScoreBreakdown(score=10.0)

        # Invalid scores
        with pytest.raises(ValidationError):
            ScoreBreakdown(score=-1.0)

        with pytest.raises(ValidationError):
            ScoreBreakdown(score=11.0)


class TestCategoryScore:
    def test_create_category_score(self):
        cat_score = CategoryScore(score=85, issue_count=3, deductions=15)

        assert cat_score.score == 85
        assert cat_score.issue_count == 3
        assert cat_score.deductions == 15

    def test_category_score_defaults(self):
        cat_score = CategoryScore(score=90)

        assert cat_score.issue_count == 0
        assert cat_score.deductions == 0

    def test_category_score_validates_range(self):
        # Valid scores
        CategoryScore(score=0)
        CategoryScore(score=50)
        CategoryScore(score=100)

        # Invalid scores
        with pytest.raises(ValidationError):
            CategoryScore(score=-1)

        with pytest.raises(ValidationError):
            CategoryScore(score=101)

    def test_category_score_to_score_breakdown(self):
        cat_score = CategoryScore(score=85, issue_count=5, deductions=15)

        breakdown = cat_score.to_score_breakdown()

        assert isinstance(breakdown, ScoreBreakdown)
        assert breakdown.score == 8.5  # 85 / 10
        assert "5 issues found" in breakdown.issues[0]


class TestScoreCard:
    def test_create_scorecard(self):
        scorecard = ScoreCard(
            reliability=90, security=85, performance=88, maintainability=92, overall=89
        )

        assert scorecard.reliability == 90
        assert scorecard.security == 85
        assert scorecard.performance == 88
        assert scorecard.maintainability == 92
        assert scorecard.overall == 89

    def test_scorecard_with_details(self):
        scorecard = ScoreCard(
            reliability=90,
            security=85,
            performance=88,
            maintainability=92,
            overall=89,
            reliability_details=CategoryScore(score=90, issue_count=2),
            security_details=CategoryScore(score=85, issue_count=3),
            performance_details=CategoryScore(score=88, issue_count=1),
            maintainability_details=CategoryScore(score=92, issue_count=1),
        )

        assert scorecard.reliability_details.issue_count == 2
        assert scorecard.security_details.issue_count == 3

    def test_scorecard_with_finding_counts(self):
        scorecard = ScoreCard(
            reliability=80,
            security=70,
            performance=85,
            maintainability=90,
            overall=81,
            total_findings=10,
            critical_count=2,
            high_count=5,
        )

        assert scorecard.total_findings == 10
        assert scorecard.critical_count == 2
        assert scorecard.high_count == 5

    def test_scorecard_grade_property(self):
        test_cases = [
            (98, "A+"),
            (92, "A"),
            (87, "A-"),
            (82, "B+"),
            (77, "B"),
            (72, "B-"),
            (67, "C+"),
            (62, "C"),
            (55, "D"),
            (45, "F"),
        ]

        for score, expected_grade in test_cases:
            scorecard = ScoreCard(
                reliability=score,
                security=score,
                performance=score,
                maintainability=score,
                overall=score,
            )
            assert scorecard.grade == expected_grade

    def test_scorecard_calculate_grade_static(self):
        assert ScoreCard.calculate_grade(98) == "A+"
        assert ScoreCard.calculate_grade(92) == "A"
        assert ScoreCard.calculate_grade(87) == "A-"
        assert ScoreCard.calculate_grade(82) == "B+"
        assert ScoreCard.calculate_grade(77) == "B"
        assert ScoreCard.calculate_grade(72) == "B-"
        assert ScoreCard.calculate_grade(67) == "C+"
        assert ScoreCard.calculate_grade(62) == "C"
        assert ScoreCard.calculate_grade(55) == "D"
        assert ScoreCard.calculate_grade(45) == "F"

    def test_scorecard_validates_ranges(self):
        # Valid
        ScoreCard(
            reliability=0, security=50, performance=75, maintainability=100, overall=56
        )

        # Invalid reliability
        with pytest.raises(ValidationError):
            ScoreCard(
                reliability=101,
                security=80,
                performance=80,
                maintainability=80,
                overall=80,
            )

    def test_scorecard_defaults(self):
        scorecard = ScoreCard(
            reliability=90, security=85, performance=88, maintainability=92, overall=89
        )

        assert scorecard.reliability_details is None
        assert scorecard.total_findings == 0
        assert scorecard.critical_count == 0
        assert scorecard.high_count == 0


class TestCodeScore:
    def test_create_code_score(self):
        code_score = CodeScore(
            overall=8.5,
            reliability=ScoreBreakdown(score=9.0),
            security=ScoreBreakdown(score=8.5),
            performance=ScoreBreakdown(score=8.8),
            maintainability=ScoreBreakdown(score=9.2),
            grade="A",
        )

        assert code_score.overall == 8.5
        assert code_score.reliability.score == 9.0
        assert code_score.grade == "A"

    def test_code_score_from_scorecard(self):
        scorecard = ScoreCard(
            reliability=90,
            security=85,
            performance=88,
            maintainability=92,
            overall=89,
            reliability_details=CategoryScore(score=90, issue_count=2),
            security_details=CategoryScore(score=85, issue_count=3),
            performance_details=CategoryScore(score=88, issue_count=1),
            maintainability_details=CategoryScore(score=92, issue_count=1),
        )

        code_score = CodeScore.from_scorecard(scorecard)

        assert code_score.overall == 8.9  # 89 / 10
        assert code_score.reliability.score == 9.0  # 90 / 10
        assert code_score.security.score == 8.5  # 85 / 10
        assert code_score.grade == "A-"

    def test_code_score_calculate_grade_static(self):
        assert CodeScore.calculate_grade(9.5) == "A+"
        assert CodeScore.calculate_grade(9.0) == "A"
        assert CodeScore.calculate_grade(8.5) == "A-"
        assert CodeScore.calculate_grade(8.0) == "B+"
        assert CodeScore.calculate_grade(7.5) == "B"
        assert CodeScore.calculate_grade(7.0) == "B-"
        assert CodeScore.calculate_grade(6.5) == "C+"
        assert CodeScore.calculate_grade(6.0) == "C"
        assert CodeScore.calculate_grade(5.5) == "D"
        assert CodeScore.calculate_grade(4.0) == "F"

    def test_code_score_validates_overall_range(self):
        # Valid
        CodeScore(
            overall=5.5,
            reliability=ScoreBreakdown(score=5.0),
            security=ScoreBreakdown(score=5.0),
            performance=ScoreBreakdown(score=5.0),
            maintainability=ScoreBreakdown(score=5.0),
            grade="D",
        )

        # Invalid
        with pytest.raises(ValidationError):
            CodeScore(
                overall=11.0,
                reliability=ScoreBreakdown(score=5.0),
                security=ScoreBreakdown(score=5.0),
                performance=ScoreBreakdown(score=5.0),
                maintainability=ScoreBreakdown(score=5.0),
                grade="A",
            )


class TestFileReview:
    def test_create_file_review(self):
        code_score = CodeScore(
            overall=8.5,
            reliability=ScoreBreakdown(score=9.0),
            security=ScoreBreakdown(score=8.5),
            performance=ScoreBreakdown(score=8.8),
            maintainability=ScoreBreakdown(score=9.2),
            grade="A",
        )

        file_review = FileReview(
            filename="auth.py",
            score=code_score,
            ai_summary="Well-structured authentication module",
            inline_comments=[
                {"line": 42, "comment": "Consider using bcrypt"},
                {"line": 78, "comment": "Add rate limiting"},
            ],
            ast_issues=["Missing docstring on line 15"],
        )

        assert file_review.filename == "auth.py"
        assert file_review.score.overall == 8.5
        assert file_review.ai_summary == "Well-structured authentication module"
        assert len(file_review.inline_comments) == 2
        assert len(file_review.ast_issues) == 1

    def test_file_review_defaults(self):
        code_score = CodeScore(
            overall=8.0,
            reliability=ScoreBreakdown(score=8.0),
            security=ScoreBreakdown(score=8.0),
            performance=ScoreBreakdown(score=8.0),
            maintainability=ScoreBreakdown(score=8.0),
            grade="B",
        )

        file_review = FileReview(
            filename="test.py", score=code_score, ai_summary="Good code"
        )

        assert file_review.inline_comments == []
        assert file_review.ast_issues == []


class TestModelConversions:
    def test_category_score_to_breakdown_conversion(self):
        test_cases = [
            (0, 0.0),
            (50, 5.0),
            (85, 8.5),
            (100, 10.0),
        ]

        for score_100, expected_score_10 in test_cases:
            cat_score = CategoryScore(score=score_100)
            breakdown = cat_score.to_score_breakdown()
            assert breakdown.score == expected_score_10

    def test_scorecard_to_code_score_preserves_grades(self):
        test_scores = [95, 90, 85, 80, 75, 70, 65, 60, 50, 40]

        for score in test_scores:
            scorecard = ScoreCard(
                reliability=score,
                security=score,
                performance=score,
                maintainability=score,
                overall=score,
            )

            code_score = CodeScore.from_scorecard(scorecard)

            # Grades should match
            assert code_score.grade == scorecard.grade

    def test_full_conversion_workflow(self):
        scorecard = ScoreCard(
            reliability=90,
            security=80,
            performance=85,
            maintainability=95,
            overall=87,
            reliability_details=CategoryScore(score=90, issue_count=1, deductions=10),
            security_details=CategoryScore(score=80, issue_count=2, deductions=20),
            performance_details=CategoryScore(score=85, issue_count=1, deductions=15),
            maintainability_details=CategoryScore(
                score=95, issue_count=0, deductions=5
            ),
            total_findings=4,
            critical_count=1,
            high_count=1,
        )

        code_score = CodeScore.from_scorecard(scorecard)

        # Check overall conversion
        assert code_score.overall == 8.7

        # Check individual categories
        assert code_score.reliability.score == 9.0
        assert code_score.security.score == 8.0
        assert code_score.performance.score == 8.5
        assert code_score.maintainability.score == 9.5

        # Check grade
        assert code_score.grade == "A-"

        # Check breakdown details preserved
        assert "1 issues found" in code_score.reliability.issues[0]


class TestJSONSerialization:
    def test_scorecard_json_serialization(self):
        scorecard = ScoreCard(
            reliability=90,
            security=85,
            performance=88,
            maintainability=92,
            overall=89,
            total_findings=5,
        )

        json_data = scorecard.model_dump()

        assert json_data["overall"] == 89
        assert json_data["security"] == 85
        assert json_data["total_findings"] == 5

    def test_code_score_json_serialization(self):
        code_score = CodeScore(
            overall=8.5,
            reliability=ScoreBreakdown(score=9.0, issues=["Issue 1"]),
            security=ScoreBreakdown(score=8.5),
            performance=ScoreBreakdown(score=8.8),
            maintainability=ScoreBreakdown(score=9.2),
            grade="A",
        )

        json_data = code_score.model_dump()

        assert json_data["overall"] == 8.5
        assert json_data["grade"] == "A"
        assert json_data["reliability"]["score"] == 9.0
        assert len(json_data["reliability"]["issues"]) == 1


class TestEdgeCases:
    def test_perfect_score(self):
        scorecard = ScoreCard(
            reliability=100,
            security=100,
            performance=100,
            maintainability=100,
            overall=100,
            total_findings=0,
        )

        assert scorecard.grade == "A+"

        code_score = CodeScore.from_scorecard(scorecard)
        assert code_score.overall == 10.0
        assert code_score.grade == "A+"

    def test_zero_score(self):
        scorecard = ScoreCard(
            reliability=0, security=0, performance=0, maintainability=0, overall=0
        )

        assert scorecard.grade == "F"

        code_score = CodeScore.from_scorecard(scorecard)
        assert code_score.overall == 0.0
        assert code_score.grade == "F"

    def test_boundary_grades(self):
        # Just above boundary
        assert ScoreCard.calculate_grade(95) == "A+"
        assert ScoreCard.calculate_grade(90) == "A"
        assert ScoreCard.calculate_grade(85) == "A-"

        # Just below boundary
        assert ScoreCard.calculate_grade(94) == "A"
        assert ScoreCard.calculate_grade(89) == "A-"
        assert ScoreCard.calculate_grade(84) == "B+"
