from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(str, Enum):
    RELIABILITY = "reliability"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"


class ReviewIssue(BaseModel):
    line: Optional[int] = None
    issue: str
    fix: str


class ReviewFinding(BaseModel):
    filename: str = Field(..., description="File path where the issue was found")
    line_number: int = Field(..., description="Line number in the file (1-indexed)")
    severity: Severity = Field(..., description="Impact level of the issue")
    category: Category = Field(..., description="Issue classification")
    title: str = Field(..., description="Short issue summary (1-2 sentences)")
    description: str = Field(..., description="Detailed explanation of the issue")
    suggestion: str = Field(
        ..., description="Actionable recommendation to fix the issue"
    )
    code_snippet: Optional[str] = Field(
        default=None, description="Optional: relevant code excerpt"
    )

    def to_review_issue(self) -> ReviewIssue:

        return ReviewIssue(
            line=self.line_number,
            issue=f"{self.title}: {self.description}",
            fix=self.suggestion,
        )


class ReviewResult(BaseModel):
    findings: List[ReviewFinding] = Field(
        default_factory=list, description="List of all detected issues"
    )
    summary: Optional[str] = Field(
        default=None, description="Optional: overall review summary"
    )
    files_analyzed: int = Field(default=0, description="Number of files analyzed")
    total_issues: int = Field(default=0, description="Total number of findings")


class AIReviewResult(BaseModel):
    summary: str
    praise: List[str] = []
    critical_issues: List[ReviewIssue] = []
    warnings: List[ReviewIssue] = []
    suggestions: List[ReviewIssue] = []
    scores: dict = {
        "reliability": 7.0,
        "security": 7.0,
        "performance": 7.0,
        "maintainability": 7.0,
    }

    @classmethod
    def from_review_result(cls, result: ReviewResult, scores: dict) -> "AIReviewResult":

        critical = []
        warnings = []
        suggestions = []

        for finding in result.findings:
            issue = finding.to_review_issue()
            if finding.severity == Severity.CRITICAL:
                critical.append(issue)
            elif finding.severity == Severity.HIGH:
                warnings.append(issue)
            else:
                suggestions.append(issue)

        return cls(
            summary=result.summary or "Code review completed",
            critical_issues=critical,
            warnings=warnings,
            suggestions=suggestions,
            scores=scores,
        )


class FileReviewRequest(BaseModel):
    filename: str
    code: str
    diff: Optional[str] = ""
    ast_issues: List[str] = []


class FileReviewResponse(BaseModel):
    filename: str
    summary: str
    grade: str
    overall_score: float
    critical_issues: List[ReviewIssue] = []
    warnings: List[ReviewIssue] = []
    suggestions: List[ReviewIssue] = []
    scores: dict = {}
