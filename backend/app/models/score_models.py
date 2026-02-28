from pydantic import BaseModel, Field
from typing import List, Optional


class ScoreBreakdown(BaseModel):
    score: float = Field(..., ge=0, le=10, description="Score from 0.0-10.0")
    issues: List[str] = []
    suggestions: List[str] = []


class CategoryScore(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Score from 0-100")
    issue_count: int = Field(default=0, description="Number of issues in this category")
    deductions: int = Field(default=0, description="Total points deducted")

    def to_score_breakdown(self) -> ScoreBreakdown:

        return ScoreBreakdown(
            score=self.score / 10.0,  # Convert 0-100 to 0-10
            issues=[f"{self.issue_count} issues found"],
            suggestions=[],
        )


class ScoreCard(BaseModel):
    reliability: int = Field(..., ge=0, le=100, description="Code reliability score")
    security: int = Field(..., ge=0, le=100, description="Security score")
    performance: int = Field(..., ge=0, le=100, description="Performance score")
    maintainability: int = Field(..., ge=0, le=100, description="Maintainability score")
    overall: int = Field(..., ge=0, le=100, description="Weighted overall score")

    # Detailed breakdown (optional, for dashboard)
    reliability_details: Optional[CategoryScore] = None
    security_details: Optional[CategoryScore] = None
    performance_details: Optional[CategoryScore] = None
    maintainability_details: Optional[CategoryScore] = None

    total_findings: int = Field(default=0, description="Total number of issues found")
    critical_count: int = Field(default=0, description="Number of critical issues")
    high_count: int = Field(default=0, description="Number of high severity issues")

    @property
    def grade(self) -> str:
        return self.calculate_grade(self.overall)

    @staticmethod
    def calculate_grade(score: int) -> str:

        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"


class CodeScore(BaseModel):
    overall: float = Field(..., ge=0, le=10)
    reliability: ScoreBreakdown
    security: ScoreBreakdown
    performance: ScoreBreakdown
    maintainability: ScoreBreakdown
    grade: str

    @classmethod
    def from_scorecard(cls, scorecard: ScoreCard) -> "CodeScore":

        return cls(
            overall=scorecard.overall / 10.0,
            reliability=scorecard.reliability_details.to_score_breakdown()
            if scorecard.reliability_details
            else ScoreBreakdown(score=scorecard.reliability / 10.0),
            security=scorecard.security_details.to_score_breakdown()
            if scorecard.security_details
            else ScoreBreakdown(score=scorecard.security / 10.0),
            performance=scorecard.performance_details.to_score_breakdown()
            if scorecard.performance_details
            else ScoreBreakdown(score=scorecard.performance / 10.0),
            maintainability=scorecard.maintainability_details.to_score_breakdown()
            if scorecard.maintainability_details
            else ScoreBreakdown(score=scorecard.maintainability / 10.0),
            grade=cls.calculate_grade(scorecard.overall / 10.0),
        )

    @staticmethod
    def calculate_grade(overall: float) -> str:
        # Convert 0-10 scale to 0-100 scale for consistent grading
        score = overall * 10

        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "A-"
        elif score >= 80:
            return "B+"
        elif score >= 75:
            return "B"
        elif score >= 70:
            return "B-"
        elif score >= 65:
            return "C+"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"


class FileReview(BaseModel):
    filename: str
    score: CodeScore
    ai_summary: str
    inline_comments: List[dict] = []
    ast_issues: List[str] = []
