import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

WEBHOOK_SECRET = "test_secret"

# A realistic minimal GitHub PR webhook payload
VALID_PAYLOAD = {
    "action": "opened",
    "number": 42,
    "repository": {"full_name": "org/repo"},
    "pull_request": {
        "title": "Refactor ETL scheduler",
        "user": {"login": "alice"},
        "head": {"sha": "abc123"},
    },
}


def make_signature(payload: dict, secret: str = WEBHOOK_SECRET) -> str:

    body = json.dumps(payload, separators=(",", ":")).encode()
    return (
        "sha256="
        + hmac.new(
            key=secret.encode(),
            msg=body,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )


def webhook_headers(payload: dict, event: str = "pull_request") -> dict:

    return {
        "Content-Type": "application/json",
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": make_signature(payload),
        "X-GitHub-Delivery": "test-delivery-id",
    }


class TestRootEndpoint:
    def test_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_service_name(self):
        response = client.get("/")
        assert response.json()["service"] == "PySenior"

    def test_returns_status_running(self):
        response = client.get("/")
        assert response.json()["status"] == "running"

    def test_returns_tagline(self):
        response = client.get("/")
        assert "tagline" in response.json()

    def test_returns_version(self):
        response = client.get("/")
        assert response.json()["version"] == "1.0.0"


class TestHealthEndpoint:
    def test_returns_200(self):
        response = client.get("/health/")
        assert response.status_code == 200

    def test_returns_status_healthy(self):
        response = client.get("/health/")
        assert response.json()["status"] == "healthy"

    def test_returns_service_name(self):
        response = client.get("/health/")
        assert response.json()["service"] == "PySenior"

    def test_returns_timestamp(self):
        response = client.get("/health/")
        assert "timestamp" in response.json()

    def test_timestamp_is_valid_iso_format(self):
        from datetime import datetime

        response = client.get("/health/")
        timestamp = response.json()["timestamp"]
        datetime.fromisoformat(timestamp)


class TestSignatureValidation:
    def test_missing_signature_returns_401(self):
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
        }
        response = client.post(
            "/webhook/github",
            json=VALID_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 401

    def test_wrong_signature_returns_401(self):
        headers = webhook_headers(VALID_PAYLOAD)
        headers["X-Hub-Signature-256"] = "sha256=invalidsignature"
        response = client.post(
            "/webhook/github",
            json=VALID_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 401

    def test_valid_signature_passes(self):
        with (
            patch("app.routes.github_webhook.github_service"),
            patch("app.routes.github_webhook.code_parser"),
            patch("app.routes.github_webhook.ai_review") as mock_ai,
            patch("app.routes.github_webhook.scoring") as mock_scoring,
            patch("app.routes.github_webhook.notification"),
        ):
            mock_ai.generate.return_value = []
            mock_scoring.calculate.return_value = MagicMock(
                reliability=90,
                security=90,
                performance=90,
                maintainability=90,
                overall=90,
            )

            response = client.post(
                "/webhook/github",
                json=VALID_PAYLOAD,
                headers=webhook_headers(VALID_PAYLOAD),
            )

        assert response.status_code == 200


class TestEventTypeFiltering:
    def test_non_pull_request_event_is_skipped(self):
        headers = webhook_headers(VALID_PAYLOAD, event="push")
        response = client.post(
            "/webhook/github",
            json=VALID_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"
        assert response.json()["reason"] == "event_not_handled"

    def test_ping_event_is_skipped(self):
        headers = webhook_headers(VALID_PAYLOAD, event="ping")
        response = client.post(
            "/webhook/github",
            json=VALID_PAYLOAD,
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"


class TestPRActionFiltering:
    def _post_with_action(self, action: str):
        payload = {**VALID_PAYLOAD, "action": action}
        return client.post(
            "/webhook/github",
            json=payload,
            headers=webhook_headers(payload),
        )

    def test_opened_action_triggers_pipeline(self):
        with (
            patch("app.routes.github_webhook.github_service"),
            patch("app.routes.github_webhook.code_parser"),
            patch("app.routes.github_webhook.ai_review") as mock_ai,
            patch("app.routes.github_webhook.scoring") as mock_scoring,
            patch("app.routes.github_webhook.notification"),
        ):
            mock_ai.generate.return_value = []
            mock_scoring.calculate.return_value = MagicMock(
                reliability=90,
                security=90,
                performance=90,
                maintainability=90,
                overall=90,
            )

            response = self._post_with_action("opened")

        assert response.status_code == 200
        assert response.json()["status"] == "review_posted"

    def test_synchronize_action_triggers_pipeline(self):
        with (
            patch("app.routes.github_webhook.github_service"),
            patch("app.routes.github_webhook.code_parser"),
            patch("app.routes.github_webhook.ai_review") as mock_ai,
            patch("app.routes.github_webhook.scoring") as mock_scoring,
            patch("app.routes.github_webhook.notification"),
        ):
            mock_ai.generate.return_value = []
            mock_scoring.calculate.return_value = MagicMock(
                reliability=90,
                security=90,
                performance=90,
                maintainability=90,
                overall=90,
            )

            response = self._post_with_action("synchronize")

        assert response.status_code == 200
        assert response.json()["status"] == "review_posted"

    def test_closed_action_is_skipped(self):
        response = self._post_with_action("closed")
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"
        assert response.json()["reason"] == "action_not_relevant"

    def test_labeled_action_is_skipped(self):
        response = self._post_with_action("labeled")
        assert response.status_code == 200
        assert response.json()["status"] == "skipped"


class TestPayloadExtraction:
    def test_malformed_payload_returns_422(self):
        # Payload is missing required nested fields
        bad_payload = {"action": "opened", "number": 42}
        response = client.post(
            "/webhook/github",
            json=bad_payload,
            headers=webhook_headers(bad_payload),
        )
        assert response.status_code == 422

    def test_missing_pr_number_returns_422(self):
        bad_payload = {**VALID_PAYLOAD}
        del bad_payload["number"]
        response = client.post(
            "/webhook/github",
            json=bad_payload,
            headers=webhook_headers(bad_payload),
        )
        assert response.status_code == 422


class TestPipelineDelegation:
    def setup_method(self):
        self.mock_score = MagicMock(
            reliability=88,
            security=60,
            performance=82,
            maintainability=90,
            overall=80,
        )
        self.mock_findings = [MagicMock(), MagicMock(), MagicMock()]

    def test_all_services_are_called(self):
        with (
            patch("app.routes.github_webhook.github_service") as mock_gh,
            patch("app.routes.github_webhook.code_parser") as mock_parser,
            patch("app.routes.github_webhook.ai_review") as mock_ai,
            patch("app.routes.github_webhook.scoring") as mock_scoring,
            patch("app.routes.github_webhook.notification") as mock_notify,
        ):
            mock_ai.generate.return_value = self.mock_findings
            mock_scoring.calculate.return_value = self.mock_score

            client.post(
                "/webhook/github",
                json=VALID_PAYLOAD,
                headers=webhook_headers(VALID_PAYLOAD),
            )

            mock_gh.get_pr_files.assert_called_once()
            mock_parser.parse.assert_called_once()
            mock_ai.generate.assert_called_once()
            mock_scoring.calculate.assert_called_once()
            mock_notify.post.assert_called_once()

    def test_response_contains_scores(self):
        with (
            patch("app.routes.github_webhook.github_service"),
            patch("app.routes.github_webhook.code_parser"),
            patch("app.routes.github_webhook.ai_review") as mock_ai,
            patch("app.routes.github_webhook.scoring") as mock_scoring,
            patch("app.routes.github_webhook.notification"),
        ):
            mock_ai.generate.return_value = self.mock_findings
            mock_scoring.calculate.return_value = self.mock_score

            response = client.post(
                "/webhook/github",
                json=VALID_PAYLOAD,
                headers=webhook_headers(VALID_PAYLOAD),
            )

        body = response.json()
        assert body["status"] == "review_posted"
        assert body["pr_number"] == 42
        assert body["repository"] == "org/repo"
        assert body["scores"]["overall"] == 80
        assert body["scores"]["security"] == 60
        assert body["findings_count"] == 3

    def test_pipeline_failure_returns_500(self):
        with (
            patch("app.routes.github_webhook.github_service") as mock_gh,
            patch("app.routes.github_webhook.code_parser"),
            patch("app.routes.github_webhook.ai_review"),
            patch("app.routes.github_webhook.scoring"),
            patch("app.routes.github_webhook.notification"),
        ):
            mock_gh.get_pr_files.side_effect = Exception("GitHub API error")

            response = client.post(
                "/webhook/github",
                json=VALID_PAYLOAD,
                headers=webhook_headers(VALID_PAYLOAD),
            )

        assert response.status_code == 500
