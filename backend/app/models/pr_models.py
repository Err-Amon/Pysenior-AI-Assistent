from pydantic import BaseModel, Field
from typing import Optional, List


class PRFile(BaseModel):
    filename: str = Field(
        ..., description="Relative path of the file in the repository"
    )
    status: str = Field(
        ..., description="File status: added, modified, removed, renamed"
    )
    additions: int = Field(default=0, description="Number of lines added")
    deletions: int = Field(default=0, description="Number of lines deleted")
    changes: int = Field(default=0, description="Total number of changes")
    patch: Optional[str] = Field(
        default=None, description="Git diff patch for the file"
    )
    content: Optional[str] = Field(
        default=None, description="Full file content after changes"
    )
    sha: str = Field(..., description="Git blob SHA of the file")

    # Additional fields for compatibility
    raw_url: Optional[str] = Field(default=None, description="Raw file URL")
    contents_url: Optional[str] = Field(default=None, description="Contents API URL")


class PullRequestData(BaseModel):
    repository: str = Field(..., description="Full repository name (owner/repo)")
    pr_number: int = Field(..., description="Pull request number")
    pr_title: str = Field(..., description="Pull request title")
    author: str = Field(..., description="GitHub username of the PR author")
    head_sha: str = Field(..., description="SHA of the head commit")
    action: str = Field(..., description="Webhook action: opened, synchronize, etc.")
    files: List[PRFile] = Field(
        default_factory=list, description="List of changed files"
    )


class PRPayload(BaseModel):
    pr_number: int
    pr_title: str
    pr_url: str
    repo_full_name: str
    base_branch: str
    head_branch: str
    author: str
    files: List[PRFile] = []


# is this code good enough??
class WebhookPayload(BaseModel):
    action: str
    number: Optional[int] = None
    pull_request: Optional[dict] = None
    repository: Optional[dict] = None
