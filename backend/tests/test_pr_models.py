import pytest
from pydantic import ValidationError

from app.models.pr_models import PRFile, PullRequestData, PRPayload, WebhookPayload


class TestPRFile:
    def test_create_valid_prfile(self):
        pr_file = PRFile(
            filename="test.py",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
            sha="abc123",
        )

        assert pr_file.filename == "test.py"
        assert pr_file.status == "modified"
        assert pr_file.additions == 10
        assert pr_file.deletions == 5
        assert pr_file.changes == 15
        assert pr_file.sha == "abc123"

    def test_prfile_with_optional_fields(self):
        pr_file = PRFile(
            filename="test.py",
            status="added",
            sha="def456",
            patch="@@ -1,3 +1,3 @@",
            content="print('hello')",
            raw_url="https://raw.githubusercontent.com/...",
            contents_url="https://api.github.com/...",
        )

        assert pr_file.patch == "@@ -1,3 +1,3 @@"
        assert pr_file.content == "print('hello')"
        assert pr_file.raw_url is not None
        assert pr_file.contents_url is not None

    def test_prfile_defaults_to_zero(self):
        pr_file = PRFile(filename="test.py", status="modified", sha="abc123")

        assert pr_file.additions == 0
        assert pr_file.deletions == 0
        assert pr_file.changes == 0

    def test_prfile_optional_fields_default_none(self):
        pr_file = PRFile(filename="test.py", status="modified", sha="abc123")

        assert pr_file.patch is None
        assert pr_file.content is None
        assert pr_file.raw_url is None
        assert pr_file.contents_url is None

    def test_prfile_requires_filename(self):
        with pytest.raises(ValidationError):
            PRFile(status="modified", sha="abc123")

    def test_prfile_requires_status(self):
        with pytest.raises(ValidationError):
            PRFile(filename="test.py", sha="abc123")

    def test_prfile_requires_sha(self):
        with pytest.raises(ValidationError):
            PRFile(filename="test.py", status="modified")


class TestPullRequestData:
    def test_create_valid_pull_request_data(self):
        pr_data = PullRequestData(
            repository="owner/repo",
            pr_number=42,
            pr_title="Fix bug",
            author="alice",
            head_sha="abc123",
            action="opened",
        )

        assert pr_data.repository == "owner/repo"
        assert pr_data.pr_number == 42
        assert pr_data.pr_title == "Fix bug"
        assert pr_data.author == "alice"
        assert pr_data.head_sha == "abc123"
        assert pr_data.action == "opened"

    def test_pull_request_data_with_files(self):
        file1 = PRFile(filename="file1.py", status="added", sha="abc")
        file2 = PRFile(filename="file2.py", status="modified", sha="def")

        pr_data = PullRequestData(
            repository="owner/repo",
            pr_number=42,
            pr_title="Fix bug",
            author="alice",
            head_sha="abc123",
            action="opened",
            files=[file1, file2],
        )

        assert len(pr_data.files) == 2
        assert pr_data.files[0].filename == "file1.py"
        assert pr_data.files[1].filename == "file2.py"

    def test_pull_request_data_files_default_empty(self):
        pr_data = PullRequestData(
            repository="owner/repo",
            pr_number=42,
            pr_title="Fix bug",
            author="alice",
            head_sha="abc123",
            action="opened",
        )

        assert pr_data.files == []

    def test_pull_request_data_requires_all_fields(self):
        with pytest.raises(ValidationError):
            PullRequestData(
                repository="owner/repo",
                pr_number=42,
                # Missing required fields
            )


class TestPRPayload:
    def test_create_valid_pr_payload(self):
        payload = PRPayload(
            pr_number=42,
            pr_title="Fix authentication",
            pr_url="https://github.com/owner/repo/pull/42",
            repo_full_name="owner/repo",
            base_branch="main",
            head_branch="feature/auth",
            author="alice",
        )

        assert payload.pr_number == 42
        assert payload.pr_title == "Fix authentication"
        assert payload.pr_url == "https://github.com/owner/repo/pull/42"
        assert payload.repo_full_name == "owner/repo"
        assert payload.base_branch == "main"
        assert payload.head_branch == "feature/auth"
        assert payload.author == "alice"

    def test_pr_payload_with_files(self):
        file1 = PRFile(filename="auth.py", status="modified", sha="abc")

        payload = PRPayload(
            pr_number=42,
            pr_title="Fix bug",
            pr_url="https://...",
            repo_full_name="owner/repo",
            base_branch="main",
            head_branch="fix",
            author="alice",
            files=[file1],
        )

        assert len(payload.files) == 1

    def test_pr_payload_files_default_empty(self):
        payload = PRPayload(
            pr_number=42,
            pr_title="Fix bug",
            pr_url="https://...",
            repo_full_name="owner/repo",
            base_branch="main",
            head_branch="fix",
            author="alice",
        )

        assert payload.files == []


class TestWebhookPayload:
    def test_create_valid_webhook_payload(self):
        payload = WebhookPayload(action="opened")

        assert payload.action == "opened"
        assert payload.number is None
        assert payload.pull_request is None
        assert payload.repository is None

    def test_webhook_payload_with_all_fields(self):
        payload = WebhookPayload(
            action="synchronize",
            number=42,
            pull_request={"title": "Fix bug", "state": "open"},
            repository={"full_name": "owner/repo", "private": False},
        )

        assert payload.action == "synchronize"
        assert payload.number == 42
        assert payload.pull_request["title"] == "Fix bug"
        assert payload.repository["full_name"] == "owner/repo"

    def test_webhook_payload_requires_action(self):
        with pytest.raises(ValidationError):
            WebhookPayload(number=42)

    def test_webhook_payload_accepts_dict_fields(self):
        payload = WebhookPayload(
            action="opened",
            pull_request={"id": 12345, "title": "Test PR", "user": {"login": "alice"}},
            repository={"id": 67890, "name": "test-repo", "owner": {"login": "owner"}},
        )

        assert isinstance(payload.pull_request, dict)
        assert isinstance(payload.repository, dict)
        assert payload.pull_request["user"]["login"] == "alice"


class TestModelIntegration:
    def test_prfile_in_pull_request_data(self):
        files = [
            PRFile(filename="file1.py", status="added", sha="abc"),
            PRFile(filename="file2.py", status="modified", sha="def"),
            PRFile(filename="file3.py", status="deleted", sha="ghi"),
        ]

        pr_data = PullRequestData(
            repository="owner/repo",
            pr_number=42,
            pr_title="Multiple changes",
            author="alice",
            head_sha="xyz789",
            action="opened",
            files=files,
        )

        assert len(pr_data.files) == 3
        assert pr_data.files[0].status == "added"
        assert pr_data.files[1].status == "modified"
        assert pr_data.files[2].status == "deleted"

    def test_pr_payload_vs_pull_request_data(self):
        # Using PullRequestData
        pr_data = PullRequestData(
            repository="owner/repo",
            pr_number=42,
            pr_title="Fix",
            author="alice",
            head_sha="abc",
            action="opened",
        )

        # Using PRPayload
        pr_payload = PRPayload(
            pr_number=42,
            pr_title="Fix",
            pr_url="https://...",
            repo_full_name="owner/repo",
            base_branch="main",
            head_branch="fix",
            author="alice",
        )

        # Both should have same pr_number and author
        assert pr_data.pr_number == pr_payload.pr_number
        assert pr_data.author == pr_payload.author

    def test_json_serialization(self):
        pr_file = PRFile(
            filename="test.py",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
            sha="abc123",
        )

        pr_data = PullRequestData(
            repository="owner/repo",
            pr_number=42,
            pr_title="Test",
            author="alice",
            head_sha="xyz",
            action="opened",
            files=[pr_file],
        )

        # Should be serializable
        json_data = pr_data.model_dump()

        assert json_data["repository"] == "owner/repo"
        assert json_data["pr_number"] == 42
        assert len(json_data["files"]) == 1
        assert json_data["files"][0]["filename"] == "test.py"

    def test_json_deserialization(self):
        json_data = {
            "repository": "owner/repo",
            "pr_number": 42,
            "pr_title": "Fix bug",
            "author": "alice",
            "head_sha": "abc123",
            "action": "opened",
            "files": [
                {
                    "filename": "test.py",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 5,
                    "changes": 15,
                    "sha": "def456",
                }
            ],
        }

        pr_data = PullRequestData(**json_data)

        assert pr_data.pr_number == 42
        assert len(pr_data.files) == 1
        assert pr_data.files[0].filename == "test.py"
