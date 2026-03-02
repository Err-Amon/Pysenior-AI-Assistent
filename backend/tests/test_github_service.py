import pytest
from unittest.mock import MagicMock, Mock, patch

from github import GithubException

from app.models.pr_models import PRFile
from app.services import github_service


class TestGetGithubClient:
    def test_creates_client_with_token(self):
        with patch("app.services.github_service.Github") as mock_github:
            github_service._get_github_client()
            mock_github.assert_called_once()

    def test_raises_error_when_token_missing(self):
        with patch("app.services.github_service.settings") as mock_settings:
            mock_settings.GITHUB_TOKEN = ""
            with pytest.raises(ValueError, match="GITHUB_TOKEN is not configured"):
                github_service._get_github_client()


class TestNormalizeFile:
    def test_converts_github_file_to_prfile(self):
        gh_file = Mock()
        gh_file.filename = "test.py"
        gh_file.status = "modified"
        gh_file.additions = 10
        gh_file.deletions = 5
        gh_file.changes = 15
        gh_file.patch = "@@ -1,3 +1,3 @@"
        gh_file.sha = "abc123"

        result = github_service._normalize_file(gh_file)

        assert isinstance(result, PRFile)
        assert result.filename == "test.py"
        assert result.status == "modified"
        assert result.additions == 10
        assert result.deletions == 5
        assert result.changes == 15
        assert result.patch == "@@ -1,3 +1,3 @@"
        assert result.sha == "abc123"
        assert result.content is None

    def test_handles_file_without_patch(self):
        gh_file = Mock(
            spec=["filename", "status", "additions", "deletions", "changes", "sha"]
        )
        gh_file.filename = "new_file.py"
        gh_file.status = "added"
        gh_file.additions = 50
        gh_file.deletions = 0
        gh_file.changes = 50
        gh_file.sha = "def456"

        result = github_service._normalize_file(gh_file)

        assert result.patch is None


class TestGetPullRequest:
    @patch("app.services.github_service._get_github_client")
    def test_fetches_pr_successfully(self, mock_client):
        mock_gh = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.title = "Test PR"

        mock_gh.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        mock_client.return_value = mock_gh

        result = github_service.get_pull_request("owner/repo", 42)

        assert result == mock_pr
        mock_gh.get_repo.assert_called_once_with("owner/repo")
        mock_repo.get_pull.assert_called_once_with(42)

    @patch("app.services.github_service._get_github_client")
    def test_raises_exception_on_not_found(self, mock_client):
        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_pull.side_effect = GithubException(404, {"message": "Not Found"})

        mock_gh.get_repo.return_value = mock_repo
        mock_client.return_value = mock_gh

        with pytest.raises(GithubException):
            github_service.get_pull_request("owner/repo", 999)


class TestGetPRFiles:
    @patch("app.services.github_service.get_pull_request")
    @patch("app.services.github_service.get_file_content")
    def test_returns_python_files_only(self, mock_get_content, mock_get_pr):
        mock_pr = Mock()

        # Create mock files
        py_file = Mock()
        py_file.filename = "script.py"
        py_file.status = "modified"
        py_file.additions = 10
        py_file.deletions = 2
        py_file.changes = 12
        py_file.patch = "@@ -1,3 +1,3 @@"
        py_file.sha = "abc123"

        non_py_file = Mock()
        non_py_file.filename = "README.md"
        non_py_file.changes = 5

        mock_pr.get_files.return_value = [py_file, non_py_file]
        mock_get_pr.return_value = mock_pr
        mock_get_content.return_value = "def test(): pass"

        result = github_service.get_pr_files("owner/repo", 42)

        assert len(result) == 1
        assert result[0].filename == "script.py"

    @patch("app.services.github_service.get_pull_request")
    @patch("app.services.github_service.get_file_content")
    def test_skips_large_files(self, mock_get_content, mock_get_pr):
        mock_pr = Mock()

        # Create a large file
        large_file = Mock()
        large_file.filename = "large.py"
        large_file.changes = 10000  # Exceeds limit

        small_file = Mock()
        small_file.filename = "small.py"
        small_file.status = "added"
        small_file.additions = 50
        small_file.deletions = 0
        small_file.changes = 50
        small_file.patch = "@@ -0,0 +1,50 @@"
        small_file.sha = "xyz789"

        mock_pr.get_files.return_value = [large_file, small_file]
        mock_get_pr.return_value = mock_pr
        mock_get_content.return_value = "def test(): pass"

        result = github_service.get_pr_files("owner/repo", 42)

        assert len(result) == 1
        assert result[0].filename == "small.py"

    @patch("app.services.github_service.get_pull_request")
    def test_returns_empty_list_for_no_python_files(self, mock_get_pr):
        mock_pr = Mock()
        mock_pr.get_files.return_value = []
        mock_pr.changed_files = 0
        mock_get_pr.return_value = mock_pr

        result = github_service.get_pr_files("owner/repo", 42)

        assert result == []


class TestGetFileContent:
    @patch("app.services.github_service._get_github_client")
    def test_fetches_file_content(self, mock_client):
        mock_gh = Mock()
        mock_repo = Mock()
        mock_content = Mock()
        mock_content.decoded_content = b"print('hello')\n"

        mock_gh.get_repo.return_value = mock_repo
        mock_repo.get_contents.return_value = mock_content
        mock_client.return_value = mock_gh

        result = github_service.get_file_content("owner/repo", "script.py", "abc123")

        assert result == "print('hello')\n"
        mock_repo.get_contents.assert_called_once_with("script.py", ref="abc123")

    @patch("app.services.github_service._get_github_client")
    def test_raises_error_for_directory(self, mock_client):
        mock_gh = Mock()
        mock_repo = Mock()
        mock_repo.get_contents.return_value = [Mock(), Mock()]  # Returns list

        mock_gh.get_repo.return_value = mock_repo
        mock_client.return_value = mock_gh

        with pytest.raises(ValueError, match="Expected file but got directory"):
            github_service.get_file_content("owner/repo", "src/", "abc123")


class TestPostReviewComment:
    @patch("app.services.github_service.get_pull_request")
    def test_posts_inline_comment(self, mock_get_pr):
        mock_pr = Mock()
        mock_commit = Mock()
        mock_pr.get_commits.return_value = [mock_commit]
        mock_get_pr.return_value = mock_pr

        github_service.post_review_comment(
            repository="owner/repo",
            pr_number=42,
            commit_sha="abc123",
            filepath="script.py",
            line_number=10,
            comment_body="This needs improvement",
        )

        mock_pr.create_review_comment.assert_called_once()
        call_args = mock_pr.create_review_comment.call_args
        assert call_args[1]["body"] == "This needs improvement"
        assert call_args[1]["path"] == "script.py"
        assert call_args[1]["line"] == 10

    @patch("app.services.github_service.get_pull_request")
    def test_logs_error_on_failure(self, mock_get_pr, caplog):
        mock_pr = Mock()
        mock_pr.get_commits.return_value = [Mock()]
        mock_pr.create_review_comment.side_effect = GithubException(
            422, {"message": "Invalid line"}
        )
        mock_get_pr.return_value = mock_pr

        # Should not raise exception
        github_service.post_review_comment(
            repository="owner/repo",
            pr_number=42,
            commit_sha="abc123",
            filepath="script.py",
            line_number=999,
            comment_body="Test",
        )

        assert "Failed to post review comment" in caplog.text


class TestPostIssueComment:
    @patch("app.services.github_service.get_pull_request")
    def test_posts_issue_comment(self, mock_get_pr):
        mock_pr = Mock()
        mock_get_pr.return_value = mock_pr

        github_service.post_issue_comment(
            repository="owner/repo",
            pr_number=42,
            comment_body="Review complete",
        )

        mock_pr.create_issue_comment.assert_called_once_with("Review complete")

    @patch("app.services.github_service.get_pull_request")
    def test_raises_exception_on_failure(self, mock_get_pr):
        mock_pr = Mock()
        mock_pr.create_issue_comment.side_effect = GithubException(
            403, {"message": "Forbidden"}
        )
        mock_get_pr.return_value = mock_pr

        with pytest.raises(GithubException):
            github_service.post_issue_comment(
                repository="owner/repo",
                pr_number=42,
                comment_body="Test",
            )
