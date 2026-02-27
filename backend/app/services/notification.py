import logging

from app.models.review_models import ReviewFinding, Severity
from app.models.score_models import ScoreCard
from app.services import github_service

logger = logging.getLogger(__name__)


def _format_score_badge(score: int) -> str:

    if score >= 90:
        return "🟢"  # Green circle
    elif score >= 75:
        return "🟡"  # Yellow circle
    elif score >= 60:
        return "🟠"  # Orange circle
    else:
        return "🔴"  # Red circle


def _format_severity_icon(severity: Severity) -> str:

    icons = {
        Severity.LOW: "ℹ️",
        Severity.MEDIUM: "⚠️",
        Severity.HIGH: "🔴",
        Severity.CRITICAL: "🚨",
    }
    return icons.get(severity, "⚠️")


def _build_summary_comment(scorecard: ScoreCard, findings: list[ReviewFinding]) -> str:

    lines = [
        "## PySenior Code Review",
        "",
        "### Overall Score",
        f"{_format_score_badge(scorecard.overall)} **{scorecard.overall}/100**",
        "",
        "### Score Breakdown",
        "",
        "| Category | Score | Issues |",
        "|----------|-------|--------|",
        f"| Reliability | {_format_score_badge(scorecard.reliability)} {scorecard.reliability}/100 | {scorecard.reliability_details.issue_count if scorecard.reliability_details else 0} |",
        f"| Security | {_format_score_badge(scorecard.security)} {scorecard.security}/100 | {scorecard.security_details.issue_count if scorecard.security_details else 0} |",
        f"| Performance | {_format_score_badge(scorecard.performance)} {scorecard.performance}/100 | {scorecard.performance_details.issue_count if scorecard.performance_details else 0} |",
        f"| Maintainability | {_format_score_badge(scorecard.maintainability)} {scorecard.maintainability}/100 | {scorecard.maintainability_details.issue_count if scorecard.maintainability_details else 0} |",
        "",
    ]

    # Add issue summary if there are findings
    if findings:
        lines.extend(
            [
                "### Issue Summary",
                "",
                f"- **Total Issues:** {scorecard.total_findings}",
                f"- **Critical:** {scorecard.critical_count}",
                f"- **High:** {scorecard.high_count}",
                "",
            ]
        )

        # Group by severity
        critical_issues = [f for f in findings if f.severity == Severity.CRITICAL]
        high_issues = [f for f in findings if f.severity == Severity.HIGH]

        if critical_issues:
            lines.append("#### Critical Issues")
            lines.append("")
            for finding in critical_issues[:5]:  # Limit to 5 in summary
                lines.append(
                    f"- **{finding.filename}:{finding.line_number}** - {finding.title}"
                )
            if len(critical_issues) > 5:
                lines.append(f"- _{len(critical_issues) - 5} more critical issues..._")
            lines.append("")

        if high_issues:
            lines.append("#### High Severity Issues")
            lines.append("")
            for finding in high_issues[:5]:  # Limit to 5 in summary
                lines.append(
                    f"- **{finding.filename}:{finding.line_number}** - {finding.title}"
                )
            if len(high_issues) > 5:
                lines.append(f"- _{len(high_issues) - 5} more high severity issues..._")
            lines.append("")

    else:
        lines.extend(
            [
                "### Great work! No issues found.",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "_Reviewed by PySenior - Your AI Senior Python Engineer_",
        ]
    )

    return "\n".join(lines)


def _build_inline_comment(finding: ReviewFinding) -> str:

    severity_icon = _format_severity_icon(finding.severity)

    lines = [
        f"{severity_icon} **{finding.severity.value.upper()}** - {finding.category.value.title()}",
        "",
        f"### {finding.title}",
        "",
        "**Issue:**",
        finding.description,
        "",
        "**Suggestion:**",
        finding.suggestion,
    ]

    if finding.code_snippet:
        lines.extend(
            [
                "",
                "**Code:**",
                "```python",
                finding.code_snippet,
                "```",
            ]
        )

    return "\n".join(lines)


def _group_findings_by_file(
    findings: list[ReviewFinding],
) -> dict[str, list[ReviewFinding]]:

    grouped = {}
    for finding in findings:
        if finding.filename not in grouped:
            grouped[finding.filename] = []
        grouped[finding.filename].append(finding)
    return grouped


def post(
    repository: str,
    pr_number: int,
    findings: list[ReviewFinding],
    score_card: ScoreCard,
) -> None:

    logger.info(
        "Posting review results | repo=%s | pr=#%s | findings=%s",
        repository,
        pr_number,
        len(findings),
    )

    # Step 1 - Post summary comment (most important)
    try:
        summary = _build_summary_comment(score_card, findings)
        github_service.post_issue_comment(repository, pr_number, summary)
        logger.info("Posted summary comment | repo=%s | pr=#%s", repository, pr_number)

    except Exception as e:
        logger.error(
            "Failed to post summary comment | repo=%s | pr=#%s | error=%s",
            repository,
            pr_number,
            str(e),
        )
        # This is critical - if we can't post the summary, something is wrong
        raise

    # Step 2 - Post inline comments for each finding
    # Group by file to organize comments
    grouped_findings = _group_findings_by_file(findings)

    posted_count = 0
    failed_count = 0

    for filename, file_findings in grouped_findings.items():
        logger.debug(
            "Posting inline comments | filename=%s | count=%s",
            filename,
            len(file_findings),
        )

        for finding in file_findings:
            try:
                comment_body = _build_inline_comment(finding)

                # Note: We're using a simplified approach here
                # In production, you'd want to:
                # 1. Verify the line exists in the PR diff
                # 2. Map the line number to the diff position
                # 3. Handle line number changes if the file was modified
                # For MVP, we'll attempt to post and log failures

                github_service.post_review_comment(
                    repository=repository,
                    pr_number=pr_number,
                    commit_sha="",  # github_service will handle getting the latest commit
                    filepath=finding.filename,
                    line_number=finding.line_number,
                    comment_body=comment_body,
                )

                posted_count += 1

            except Exception as e:
                failed_count += 1
                logger.warning(
                    "Failed to post inline comment | repo=%s | pr=#%s | file=%s | line=%s | error=%s",
                    repository,
                    pr_number,
                    finding.filename,
                    finding.line_number,
                    str(e),
                )
                # Continue with other comments

    logger.info(
        "Review posting completed | repo=%s | pr=#%s | posted=%s | failed=%s",
        repository,
        pr_number,
        posted_count,
        failed_count,
    )

    # If we posted the summary but all inline comments failed, that's still acceptable
    # The user can see the summary and findings list
    if failed_count > 0:
        logger.warning(
            "Some inline comments failed to post | repo=%s | pr=#%s | failed_count=%s",
            repository,
            pr_number,
            failed_count,
        )
