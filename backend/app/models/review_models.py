from pydantic import BaseModel
from typing import List, Optional


class ReviewIssue(BaseModel):
    line: Optional[int] = None
    issue: str
    fix: str


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