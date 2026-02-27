from pydantic import BaseModel
from typing import List


class ScoreBreakdown(BaseModel):
    score: float  # 0.0 - 10.0
    issues: List[str] = []
    suggestions: List[str] = []


class CodeScore(BaseModel):
    overall: float
    reliability: ScoreBreakdown
    security: ScoreBreakdown
    performance: ScoreBreakdown
    maintainability: ScoreBreakdown
    grade: str

    @classmethod
    def calculate_grade(cls, overall: float) -> str:
        if overall >= 9.0:
            return "A+"
        elif overall >= 8.0:
            return "A"
        elif overall >= 7.0:
            return "B"
        elif overall >= 6.0:
            return "C"
        elif overall >= 5.0:
            return "D"
        else:
            return "F"


class FileReview(BaseModel):
    filename: str
    score: CodeScore
    ai_summary: str
    inline_comments: List[dict] = []
    ast_issues: List[str] = []