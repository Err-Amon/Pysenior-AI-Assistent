from fastapi import APIRouter, HTTPException
import logging
from typing import List

from app.services import ai_review, code_parser
from app.models.review_models import ReviewFinding, ReviewResult
from app.models.pr_models import PRFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class FileContent(BaseModel):
    filename: str
    content: str


class ReviewRequest(BaseModel):
    files: List[FileContent]


class ReviewResponse(BaseModel):
    findings: List[ReviewFinding]
    summary: str


@router.post("/review", response_model=ReviewResponse, tags=["AI Review"])
async def review_code(request: ReviewRequest) -> ReviewResponse:
    try:
        logger.info(f"Received review request for {len(request.files)} files")

        # Prepare files for parsing (convert to PRFile format)
        files = []
        for file_data in request.files:
            files.append(
                PRFile(
                    filename=file_data.filename,
                    status="modified",
                    additions=0,
                    deletions=0,
                    changes=0,
                    content=file_data.content,
                    sha="",
                )
            )

        # Parse code
        parsed_files = code_parser.parse(files)
        logger.debug(f"Successfully parsed {len(parsed_files)} files")

        # Generate AI review
        findings = ai_review.generate(parsed_files)
        logger.info(f"Generated {len(findings)} findings")

        # Prepare response
        summary = (
            f"Code review complete. Found {len(findings)} issues."
            if findings
            else "Code review complete. No issues found."
        )

        return ReviewResponse(findings=findings, summary=summary)

    except Exception as e:
        logger.exception(f"Error during code review: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Code review failed: {str(e)}")


@router.get("/health", tags=["AI Review"])
async def ai_review_health() -> dict:
    return {
        "status": "healthy",
        "service": "ai_review",
        "providers": ["openai", "anthropic", "gemini", "groq", "openrouter"],
    }
