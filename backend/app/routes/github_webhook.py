import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import get_settings
from app.services import ai_review, code_parser, github_service, notification, scoring

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_signature(raw_body: bytes, signature_header: str | None) -> None:

    if not signature_header:
        logger.warning("Webhook received with no signature header.")
        raise HTTPException(status_code=401, detail="Missing webhook signature.")

    settings = get_settings()

    expected = (
        "sha256="
        + hmac.new(
            key=settings.GITHUB_WEBHOOK_SECRET.encode(),
            msg=raw_body,
            digestmod=hashlib.sha256,
        ).hexdigest()
    )

    logger.debug("Raw body for signature check: %s", raw_body)
    logger.debug("Expected signature: %s", expected)
    logger.debug("Received signature: %s", signature_header)

    if not hmac.compare_digest(expected, signature_header):
        logger.warning("Webhook signature mismatch — request rejected.")
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")


def _extract_pr_data(payload: dict) -> dict:

    try:
        return {
            "action": payload["action"],
            "pr_number": payload["number"],
            "repository": payload["repository"]["full_name"],
            "pr_title": payload["pull_request"]["title"],
            "author": payload["pull_request"]["user"]["login"],
            "head_sha": payload["pull_request"]["head"]["sha"],
        }
    except KeyError as e:
        logger.error("Malformed webhook payload — missing field: %s", e)
        raise HTTPException(
            status_code=422,
            detail=f"Missing required field in payload: {e}",
        )


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict:

    raw_body = await request.body()

    # Step 1 — Validate signature before doing anything else
    _verify_signature(raw_body, x_hub_signature_256)

    logger.info(
        "Webhook received | event=%s | delivery=%s",
        x_github_event,
        x_github_delivery,
    )

    # Step 2 — Only handle pull_request events
    if x_github_event != "pull_request":
        logger.info("Event type '%s' is not handled — skipping.", x_github_event)
        return {"status": "skipped", "reason": "event_not_handled"}

    payload = await request.json()
    pr_data = _extract_pr_data(payload)

    # Step 3 — Only process relevant PR actions
    if pr_data["action"] not in ("opened", "synchronize"):
        logger.info(
            "PR action '%s' does not require review — skipping.", pr_data["action"]
        )
        return {"status": "skipped", "reason": "action_not_relevant"}

    logger.info(
        "Starting review pipeline | repo=%s | pr=#%s | author=%s",
        pr_data["repository"],
        pr_data["pr_number"],
        pr_data["author"],
    )

    # Step 4 — Run the pipeline. Each step delegates to its service.
    # No logic lives here — only the order of calls.
    try:
        files = github_service.get_pr_files(
            repository=pr_data["repository"],
            pr_number=pr_data["pr_number"],
        )

        parsed = code_parser.parse(files)

        findings = ai_review.generate(parsed)

        score_card = scoring.calculate(findings)

        notification.post(
            repository=pr_data["repository"],
            pr_number=pr_data["pr_number"],
            findings=findings,
            score_card=score_card,
        )

    except Exception as e:
        logger.exception(
            "Pipeline failed | repo=%s | pr=#%s | error=%s",
            pr_data["repository"],
            pr_data["pr_number"],
            str(e),
        )
        raise HTTPException(status_code=500, detail="Internal pipeline failure.")

    logger.info(
        "Review completed | repo=%s | pr=#%s | overall_score=%s",
        pr_data["repository"],
        pr_data["pr_number"],
        score_card.overall,
    )

    return {
        "status": "review_posted",
        "pr_number": pr_data["pr_number"],
        "repository": pr_data["repository"],
        "scores": {
            "reliability": score_card.reliability,
            "security": score_card.security,
            "performance": score_card.performance,
            "maintainability": score_card.maintainability,
            "overall": score_card.overall,
        },
        "findings_count": len(findings),
<<<<<<< HEAD
    }
=======
    }
>>>>>>> 71340ac23da0f14611447206728c7858dd1e1515
