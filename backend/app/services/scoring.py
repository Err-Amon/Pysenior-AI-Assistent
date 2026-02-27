import logging
from collections import defaultdict

from app.models.review_models import Category, ReviewFinding, Severity
from app.models.score_models import CategoryScore, ScoreCard

logger = logging.getLogger(__name__)


# Scoring configuration
# Each severity level has a deduction value per category
DEDUCTION_MATRIX = {
    Severity.LOW: 2,
    Severity.MEDIUM: 5,
    Severity.HIGH: 10,
    Severity.CRITICAL: 20,
}

# Starting score for each category
BASE_SCORE = 100

# Minimum score floor (never go below this)
MIN_SCORE = 0

# Weights for calculating overall score
CATEGORY_WEIGHTS = {
    Category.RELIABILITY: 0.30,
    Category.SECURITY: 0.35,
    Category.PERFORMANCE: 0.20,
    Category.MAINTAINABILITY: 0.15,
}


def _calculate_category_score(
    findings: list[ReviewFinding],
    category: Category,
) -> CategoryScore:

    category_findings = [f for f in findings if f.category == category]

    total_deduction = 0
    for finding in category_findings:
        deduction = DEDUCTION_MATRIX[finding.severity]
        total_deduction += deduction

    score = max(BASE_SCORE - total_deduction, MIN_SCORE)

    return CategoryScore(
        score=score,
        issue_count=len(category_findings),
        deductions=total_deduction,
    )


def _calculate_overall_score(category_scores: dict[Category, int]) -> int:

    weighted_sum = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        score = category_scores.get(category, BASE_SCORE)
        weighted_sum += score * weight

    overall = int(round(weighted_sum))
    return max(min(overall, BASE_SCORE), MIN_SCORE)


def _count_by_severity(findings: list[ReviewFinding]) -> dict[Severity, int]:

    counts = defaultdict(int)
    for finding in findings:
        counts[finding.severity] += 1
    return dict(counts)


def calculate(findings: list[ReviewFinding]) -> ScoreCard:

    logger.info("Calculating scores | total_findings=%s", len(findings))

    # Handle empty findings (perfect code!)
    if not findings:
        perfect_score = CategoryScore(score=BASE_SCORE, issue_count=0, deductions=0)

        return ScoreCard(
            reliability=BASE_SCORE,
            security=BASE_SCORE,
            performance=BASE_SCORE,
            maintainability=BASE_SCORE,
            overall=BASE_SCORE,
            reliability_details=perfect_score,
            security_details=perfect_score,
            performance_details=perfect_score,
            maintainability_details=perfect_score,
            total_findings=0,
            critical_count=0,
            high_count=0,
        )

    # Calculate category scores
    reliability_details = _calculate_category_score(findings, Category.RELIABILITY)
    security_details = _calculate_category_score(findings, Category.SECURITY)
    performance_details = _calculate_category_score(findings, Category.PERFORMANCE)
    maintainability_details = _calculate_category_score(
        findings, Category.MAINTAINABILITY
    )

    # Build category scores dict for overall calculation
    category_scores = {
        Category.RELIABILITY: reliability_details.score,
        Category.SECURITY: security_details.score,
        Category.PERFORMANCE: performance_details.score,
        Category.MAINTAINABILITY: maintainability_details.score,
    }

    # Calculate overall score
    overall = _calculate_overall_score(category_scores)

    # Count severity distribution
    severity_counts = _count_by_severity(findings)

    scorecard = ScoreCard(
        reliability=reliability_details.score,
        security=security_details.score,
        performance=performance_details.score,
        maintainability=maintainability_details.score,
        overall=overall,
        reliability_details=reliability_details,
        security_details=security_details,
        performance_details=performance_details,
        maintainability_details=maintainability_details,
        total_findings=len(findings),
        critical_count=severity_counts.get(Severity.CRITICAL, 0),
        high_count=severity_counts.get(Severity.HIGH, 0),
    )

    logger.info(
        "Scores calculated | overall=%s | reliability=%s | security=%s | performance=%s | maintainability=%s",
        scorecard.overall,
        scorecard.reliability,
        scorecard.security,
        scorecard.performance,
        scorecard.maintainability,
    )

    return scorecard
