import logging
from typing import Any

from github import Github, GithubException
from github.PullRequest import PullRequest

from app.config import get_settings
from app.models.pr_models import PRFile

logger = logging.getLogger(__name__)

settings = get_settings()


def _get_github_client() -> Github:

    if not settings.GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN is not configured")

    return Github(settings.GITHUB_TOKEN)


def _normalize_file(gh_file: Any) -> PRFile:

    return PRFile(
        filename=gh_file.filename,
        status=gh_file.status,
        additions=gh_file.additions,
        deletions=gh_file.deletions,
        changes=gh_file.changes,
        patch=gh_file.patch if hasattr(gh_file, "patch") else None,
        content=None,  # Will be fetched separately if needed
        sha=gh_file.sha,
    )


def get_pull_request(repository: str, pr_number: int) -> PullRequest:

    try:
        client = _get_github_client()
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        logger.info(
            "Fetched PR | repo=%s | pr=#%s | title=%s",
            repository,
            pr_number,
            pr.title,
        )
        return pr

    except GithubException as e:
        logger.error(
            "Failed to fetch PR | repo=%s | pr=#%s | status=%s | message=%s",
            repository,
            pr_number,
            e.status,
            e.data.get("message", "Unknown error"),
        )
        raise


def get_pr_files(repository: str, pr_number: int) -> list[PRFile]:

    pr = get_pull_request(repository, pr_number)

    files = []
    for gh_file in pr.get_files():
        # Filter by file size to avoid processing huge files
        if gh_file.changes > settings.MAX_FILE_SIZE_KB * 10:  # Rough heuristic
            logger.warning(
                "Skipping large file | filename=%s | changes=%s",
                gh_file.filename,
                gh_file.changes,
            )
            continue

        # Only process Python files
        if not gh_file.filename.endswith(".py"):
            logger.debug("Skipping non-Python file | filename=%s", gh_file.filename)
            continue

        normalized = _normalize_file(gh_file)
        files.append(normalized)

    logger.info(
        "Retrieved PR files | repo=%s | pr=#%s | total_files=%s | python_files=%s",
        repository,
        pr_number,
        pr.changed_files,
        len(files),
    )

    return files


def get_file_content(repository: str, filepath: str, ref: str) -> str:

    try:
        client = _get_github_client()
        repo = client.get_repo(repository)
        content = repo.get_contents(filepath, ref=ref)

        if isinstance(content, list):
            raise ValueError(f"Expected file but got directory: {filepath}")

        decoded = content.decoded_content.decode("utf-8")
        logger.debug(
            "Fetched file content | repo=%s | file=%s | ref=%s",
            repository,
            filepath,
            ref,
        )
        return decoded

    except GithubException as e:
        logger.error(
            "Failed to fetch file content | repo=%s | file=%s | ref=%s | status=%s",
            repository,
            filepath,
            ref,
            e.status,
        )
        raise


def post_review_comment(
    repository: str,
    pr_number: int,
    commit_sha: str,
    filepath: str,
    line_number: int,
    comment_body: str,
) -> None:

    try:
        pr = get_pull_request(repository, pr_number)

        pr.create_review_comment(
            body=comment_body,
            commit=pr.get_commits()[0],  # Use the latest commit
            path=filepath,
            line=line_number,
        )

        logger.info(
            "Posted review comment | repo=%s | pr=#%s | file=%s | line=%s",
            repository,
            pr_number,
            filepath,
            line_number,
        )

    except GithubException as e:
        logger.error(
            "Failed to post review comment | repo=%s | pr=#%s | file=%s | line=%s | status=%s",
            repository,
            pr_number,
            filepath,
            line_number,
            e.status,
        )
        # Don't raise - we don't want one failed comment to break the entire review
        # Just log and continue


def post_issue_comment(repository: str, pr_number: int, comment_body: str) -> None:

    try:
        pr = get_pull_request(repository, pr_number)
        pr.create_issue_comment(comment_body)

        logger.info(
            "Posted issue comment | repo=%s | pr=#%s",
            repository,
            pr_number,
        )

    except GithubException as e:
        logger.error(
            "Failed to post issue comment | repo=%s | pr=#%s | status=%s",
            repository,
            pr_number,
            e.status,
        )
        raise
