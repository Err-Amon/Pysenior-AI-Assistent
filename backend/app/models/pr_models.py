from pydantic import BaseModel
from typing import Optional, List


class PRFile(BaseModel):
    filename: str
    status: str
    patch: Optional[str] = None
    raw_url: Optional[str] = None
    contents_url: Optional[str] = None
    changes: int = 0
    additions: int = 0
    deletions: int = 0


class PRPayload(BaseModel):
    pr_number: int
    pr_title: str
    pr_url: str
    repo_full_name: str
    base_branch: str
    head_branch: str
    author: str
    files: List[PRFile] = []


class WebhookPayload(BaseModel):
    action: str
    number: Optional[int] = None
    pull_request: Optional[dict] = None
    repository: Optional[dict] = None