from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


OUTPUT_DIR = Path("outputs")
EMAIL_PREVIEW_DIR = OUTPUT_DIR / "email_preview"
LONDON_TZ = ZoneInfo("Europe/London")
RUN_TYPE_LABELS = {
    "eu_open": "EU Open",
    "us_open": "US Open",
    "us_close": "US Close",
}
RECIPIENT_PLACEHOLDER = ["<recipient-list-placeholder>"]
BODY_PREVIEW_CHAR_LIMIT = 1200


def briefing_path_for_run_type(run_type: str) -> Path:
    return OUTPUT_DIR / f"{run_type}_briefing.md"


def preview_path_for_run_type(run_type: str) -> Path:
    return EMAIL_PREVIEW_DIR / f"{run_type}_email.md"


def build_email_from_briefing(
    run_type: str,
    briefing_path: Path | None = None,
    london_now: datetime | None = None,
) -> dict[str, Any]:
    source_path = briefing_path or briefing_path_for_run_type(run_type)
    if not source_path.exists():
        raise FileNotFoundError(
            f"Briefing file not found: {source_path}. Run write_briefing first."
        )

    london_timestamp = london_now or datetime.now(LONDON_TZ)
    run_label = RUN_TYPE_LABELS[run_type]
    body = source_path.read_text(encoding="utf-8")
    subject = (
        f"MCD Equities Briefing | {run_label} | "
        f"{london_timestamp:%Y-%m-%d %H:%M London}"
    )

    return {
        "recipients": RECIPIENT_PLACEHOLDER,
        "subject": subject,
        "body": body,
        "source_briefing_path": source_path,
    }


def render_email_preview_markdown(email_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Email Delivery Preview",
            "",
            f"Recipient list placeholder: {', '.join(email_payload['recipients'])}",
            f"Subject: {email_payload['subject']}",
            f"Source briefing path: {email_payload['source_briefing_path']}",
            "",
            "## Email Body",
            "",
            email_payload["body"].rstrip(),
            "",
        ]
    )


def save_email_preview(
    email_payload: dict[str, Any],
    run_type: str,
) -> Path:
    preview_path = preview_path_for_run_type(run_type)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        render_email_preview_markdown(email_payload),
        encoding="utf-8",
    )
    return preview_path


def preview_body(body: str, char_limit: int = BODY_PREVIEW_CHAR_LIMIT) -> str:
    if len(body) <= char_limit:
        return body

    preview_lines: list[str] = []
    current_length = 0
    for line in body.splitlines():
        next_length = current_length + len(line) + 1
        if next_length > char_limit:
            break

        preview_lines.append(line)
        current_length = next_length

    return "\n".join(preview_lines).rstrip() + "\n..."


def format_dry_run_summary(email_payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Email delivery dry run:",
            f"Recipient list placeholder: {', '.join(email_payload['recipients'])}",
            f"Subject: {email_payload['subject']}",
            f"Source briefing path: {email_payload['source_briefing_path']}",
            f"Saved preview path: {email_payload['preview_path']}",
            "Body preview:",
            preview_body(email_payload["body"]),
        ]
    )


def email_dry_run(run_type: str) -> dict[str, Any]:
    email_payload = build_email_from_briefing(run_type=run_type)
    preview_path = save_email_preview(email_payload, run_type=run_type)
    email_payload["preview_path"] = preview_path
    return email_payload
