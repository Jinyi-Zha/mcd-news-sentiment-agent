import csv
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


OUTPUT_DIR = Path("outputs")
RUN_SUMMARY_PATH = OUTPUT_DIR / "run_summary.md"
EMAIL_PREVIEW_DIR = OUTPUT_DIR / "email_preview"
MACRO_CALENDAR_PATH = Path("data/processed/macro_calendar.csv")
LONDON_TZ = ZoneInfo("Europe/London")
EXPECTED_STAGES = (
    "pull_yahoo",
    "pull_cnbc",
    "combine_raw",
    "filter_equities",
    "filter_recent",
    "ticker_frequency",
    "headline_repetition",
    "macro_calendar",
    "write_briefing",
    "email_dry_run",
)


def briefing_path_for_run_type(run_type: str) -> Path:
    return OUTPUT_DIR / f"{run_type}_briefing.md"


def email_preview_path_for_run_type(run_type: str) -> Path:
    return EMAIL_PREVIEW_DIR / f"{run_type}_email.md"


def archive_summary_path_for_run_type(run_type: str, london_now: datetime) -> Path:
    date_part = london_now.strftime("%Y-%m-%d")
    time_part = london_now.strftime("%Y-%m-%d_%H%M")
    return OUTPUT_DIR / "archive" / date_part / f"run_summary_{run_type}_{time_part}.md"


def latest_briefing_archive_path(run_type: str) -> Path | None:
    archive_paths = sorted(
        (OUTPUT_DIR / "archive").glob(f"*/{run_type}_briefing_*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return archive_paths[0] if archive_paths else None


def read_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8")


def macro_calendar_event_count(path: Path = MACRO_CALENDAR_PATH) -> int:
    if not path.exists():
        return 0

    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return sum(1 for row in csv.DictReader(csv_file) if row.get("event", "").strip())


def normalize_heading_line(line: str) -> str:
    return line.strip().lstrip("#").strip().upper()


def has_section_heading(text: str, accepted_headings: tuple[str, ...]) -> bool:
    normalized_headings = {heading.upper() for heading in accepted_headings}
    return any(
        normalize_heading_line(line) in normalized_headings
        for line in text.splitlines()
    )


def count_numbered_items(section_text: str) -> int:
    return sum(
        1
        for line in section_text.splitlines()
        if line.strip() and line.lstrip()[0].isdigit() and "." in line.split()[0]
    )


def section_between(text: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    if start_marker not in text:
        return ""

    after_start = text.split(start_marker, 1)[1]
    end_positions = [
        after_start.find(marker)
        for marker in end_markers
        if marker in after_start
    ]
    if not end_positions:
        return after_start

    return after_start[: min(end_positions)]


def first_matching_section(
    text: str,
    start_markers: tuple[str, ...],
    end_markers: tuple[str, ...],
) -> str:
    for start_marker in start_markers:
        section_text = section_between(
            text=text,
            start_marker=start_marker,
            end_markers=end_markers,
        )
        if section_text:
            return section_text

    return ""


def infer_briefing_counts(briefing_text: str) -> dict[str, int]:
    top_theme_section = first_matching_section(
        briefing_text,
        ("TOP MARKET THEMES", "TOP HEADLINES"),
        ("KEY TICKERS TO WATCH", "KEY TICKERS", "MACRO WATCH", "NEXT WATCH POINTS"),
    )
    key_ticker_section = first_matching_section(
        briefing_text,
        ("KEY TICKERS TO WATCH", "KEY TICKERS"),
        ("MACRO WATCH", "MACRO CALENDAR", "NEXT WATCH POINTS"),
    )
    macro_section = first_matching_section(
        briefing_text,
        ("MACRO WATCH", "MACRO CALENDAR"),
        ("NEXT WATCH POINTS", "Generated automatically."),
    )
    macro_event_count = sum(
        1
        for line in macro_section.splitlines()
        if line.strip() and " — " in line and line[:1].isdigit()
    )

    return {
        "top_headlines_included": count_numbered_items(top_theme_section),
        "key_tickers_included": count_numbered_items(key_ticker_section),
        "macro_events_included": macro_event_count,
        "line_count": len(briefing_text.splitlines()) if briefing_text else 0,
    }


def merge_data_summary(
    briefing_text: str,
    briefing_summary: dict[str, Any] | None,
) -> dict[str, int]:
    inferred_summary = infer_briefing_counts(briefing_text)
    if not briefing_summary:
        return inferred_summary

    return {
        "top_headlines_included": int(
            briefing_summary.get(
                "top_headlines_included",
                inferred_summary["top_headlines_included"],
            )
        ),
        "key_tickers_included": int(
            briefing_summary.get(
                "key_tickers_included",
                inferred_summary["key_tickers_included"],
            )
        ),
        "macro_events_included": int(
            briefing_summary.get(
                "macro_events_included",
                inferred_summary["macro_events_included"],
            )
        ),
        "line_count": int(briefing_summary.get("line_count", inferred_summary["line_count"])),
    }


def check_status(ok: bool, failed: bool = False) -> str:
    if failed:
        return "FAILED"
    if ok:
        return "OK"
    return "WARNING"


def warning_message(check_name: str) -> str:
    messages = {
        "Briefing file exists": "briefing file missing",
        "Briefing is not empty": "briefing file empty",
        "Executive summary section exists": "executive summary section missing",
        "Top market themes section exists": "top market themes section missing",
        "Key tickers section exists": "key tickers section missing",
        "Macro watch section exists": "macro watch section missing",
        "Next watch points section exists": "next watch points section missing",
        "At least 3 market themes": "fewer than 3 market themes found",
        "At least 3 key tickers": "fewer than 3 key tickers found",
        "At least 1 macro event": "fewer than 1 macro event found",
        "Email preview exists": "email preview not found",
        "Run summary exists": "run summary not found",
    }
    return messages.get(check_name, check_name.lower())


def validation_status(quality_checks: dict[str, str]) -> str:
    if any(status == "FAILED" for status in quality_checks.values()):
        return "Failed"
    if any(status == "WARNING" for status in quality_checks.values()):
        return "Warning"
    return "Success"


def build_quality_checks(
    briefing_path: Path,
    briefing_text: str,
    email_preview_path: Path,
    run_summary_path: Path,
    data_summary: dict[str, int],
    expect_run_summary: bool = True,
) -> tuple[dict[str, str], list[str]]:
    briefing_exists = briefing_path.exists()
    briefing_not_empty = bool(briefing_text.strip())
    macro_csv_exists = MACRO_CALENDAR_PATH.exists()
    macro_csv_events = macro_calendar_event_count() if macro_csv_exists else 0
    macro_events_in_briefing = data_summary["macro_events_included"]
    legacy_compact_format = (
        has_section_heading(briefing_text, ("TOP HEADLINES",))
        and has_section_heading(briefing_text, ("KEY TICKERS",))
        and has_section_heading(briefing_text, ("MACRO CALENDAR",))
    )

    checks = {
        "Briefing file exists": check_status(
            briefing_exists,
            failed=not briefing_exists,
        ),
        "Briefing is not empty": check_status(
            briefing_not_empty,
            failed=briefing_exists and not briefing_not_empty,
        ),
        "Executive summary section exists": check_status(
            has_section_heading(briefing_text, ("EXECUTIVE SUMMARY",))
            or legacy_compact_format
        ),
        "Top market themes section exists": check_status(
            has_section_heading(briefing_text, ("TOP MARKET THEMES", "TOP HEADLINES"))
        ),
        "Key tickers section exists": check_status(
            has_section_heading(briefing_text, ("KEY TICKERS TO WATCH", "KEY TICKERS"))
        ),
        "Macro watch section exists": check_status(
            has_section_heading(briefing_text, ("MACRO WATCH", "MACRO CALENDAR"))
        ),
        "Next watch points section exists": check_status(
            has_section_heading(briefing_text, ("NEXT WATCH POINTS",))
            or legacy_compact_format
        ),
        "At least 3 market themes": check_status(
            data_summary["top_headlines_included"] >= 3
        ),
        "At least 3 key tickers": check_status(
            data_summary["key_tickers_included"] >= 3
        ),
        "At least 1 macro event": check_status(
            not macro_csv_exists or macro_csv_events == 0 or macro_events_in_briefing >= 1
        ),
        "Email preview exists": check_status(email_preview_path.exists()),
    }
    if expect_run_summary:
        checks["Run summary exists"] = check_status(run_summary_path.exists())

    warnings = [
        f"{status}: {warning_message(check_name)}"
        for check_name, status in checks.items()
        if status != "OK"
    ]

    return checks, warnings


def validate_briefing_quality(
    run_type: str,
    briefing_summary: dict[str, Any] | None = None,
    email_payload: dict[str, Any] | None = None,
    expect_run_summary: bool = True,
) -> dict[str, Any]:
    briefing_path = Path(
        briefing_summary.get("output_path", briefing_path_for_run_type(run_type))
        if briefing_summary
        else briefing_path_for_run_type(run_type)
    )
    email_preview_path = Path(
        email_payload.get("preview_path", email_preview_path_for_run_type(run_type))
        if email_payload
        else email_preview_path_for_run_type(run_type)
    )
    briefing_text = read_text_if_exists(briefing_path)
    data_summary = merge_data_summary(
        briefing_text=briefing_text,
        briefing_summary=briefing_summary,
    )
    quality_checks, warnings = build_quality_checks(
        briefing_path=briefing_path,
        briefing_text=briefing_text,
        email_preview_path=email_preview_path,
        run_summary_path=RUN_SUMMARY_PATH,
        data_summary=data_summary,
        expect_run_summary=expect_run_summary,
    )
    return {
        "run_type": run_type,
        "briefing_path": str(briefing_path),
        "email_preview_path": str(email_preview_path),
        "run_summary_path": str(RUN_SUMMARY_PATH),
        "overall_status": validation_status(quality_checks),
        "quality_checks": quality_checks,
        "warnings": warnings,
        **data_summary,
    }


def render_run_summary(
    run_type: str,
    london_now: datetime,
    output_files: dict[str, Path | None],
    data_summary: dict[str, int],
    quality_checks: dict[str, str],
    warnings: list[str],
) -> str:
    overall_status = validation_status(quality_checks)
    stage_lines = [f"- {stage}" for stage in EXPECTED_STAGES]
    output_lines = [
        f"- Briefing: {output_files['briefing']}",
        f"- Archive briefing: {output_files['archive_briefing'] or 'Not found'}",
        f"- Email preview: {output_files['email_preview']}",
        f"- Run summary: {output_files['run_summary']}",
        f"- Archive run summary: {output_files['archive_run_summary']}",
    ]
    quality_lines = [
        f"- {check_name}: {status}"
        for check_name, status in quality_checks.items()
    ]
    warning_lines = [f"- {warning}" for warning in warnings] or ["- None"]

    return "\n".join(
        [
            "# MCD News & Sentiment Agent — Run Summary",
            "",
            f"Project name: MCD News & Sentiment Agent",
            f"Run type: {run_type}",
            f"Run time: {london_now:%Y-%m-%d %H:%M %Z}",
            f"Overall status: {overall_status}",
            "",
            "## Pipeline Stages",
            *stage_lines,
            "",
            "## Pipeline Outputs",
            *output_lines,
            "",
            "## Data Summary",
            f"- Top headlines included: {data_summary['top_headlines_included']}",
            f"- Key tickers included: {data_summary['key_tickers_included']}",
            f"- Macro events included: {data_summary['macro_events_included']}",
            f"- Approximate briefing line count: {data_summary['line_count']}",
            "",
            "## Quality Checks",
            *quality_lines,
            "",
            "## Warnings",
            *warning_lines,
            "",
            "## Notes",
            "Generated automatically. Not a trade recommendation.",
            "",
        ]
    )


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def create_run_summary(
    run_type: str,
    briefing_summary: dict[str, Any] | None = None,
    email_payload: dict[str, Any] | None = None,
    london_now: datetime | None = None,
) -> tuple[Path, dict[str, Any]]:
    resolved_london_now = london_now or datetime.now(LONDON_TZ)
    briefing_path = Path(
        briefing_summary.get("output_path", briefing_path_for_run_type(run_type))
        if briefing_summary
        else briefing_path_for_run_type(run_type)
    )
    archive_briefing_path = Path(briefing_summary["archive_path"]) if briefing_summary else latest_briefing_archive_path(run_type)
    email_preview_path = Path(
        email_payload.get("preview_path", email_preview_path_for_run_type(run_type))
        if email_payload
        else email_preview_path_for_run_type(run_type)
    )
    archive_run_summary_path = archive_summary_path_for_run_type(
        run_type=run_type,
        london_now=resolved_london_now,
    )

    briefing_text = read_text_if_exists(briefing_path)
    data_summary = merge_data_summary(
        briefing_text=briefing_text,
        briefing_summary=briefing_summary,
    )
    quality_checks, warnings = build_quality_checks(
        briefing_path=briefing_path,
        briefing_text=briefing_text,
        email_preview_path=email_preview_path,
        run_summary_path=RUN_SUMMARY_PATH,
        data_summary=data_summary,
        expect_run_summary=False,
    )
    quality_checks["Run summary exists"] = "OK"
    output_files = {
        "briefing": briefing_path,
        "archive_briefing": archive_briefing_path,
        "email_preview": email_preview_path,
        "run_summary": RUN_SUMMARY_PATH,
        "archive_run_summary": archive_run_summary_path,
    }
    summary_text = render_run_summary(
        run_type=run_type,
        london_now=resolved_london_now,
        output_files=output_files,
        data_summary=data_summary,
        quality_checks=quality_checks,
        warnings=warnings,
    )

    saved_path = write_text(RUN_SUMMARY_PATH, summary_text)
    archive_path = write_text(archive_run_summary_path, summary_text)
    summary = {
        "output_path": str(saved_path),
        "archive_path": str(archive_path),
        "overall_status": validation_status(quality_checks),
        "quality_checks": quality_checks,
        "warnings": warnings,
        **data_summary,
    }
    return saved_path, summary


def format_validation_summary(summary: dict[str, Any]) -> str:
    warning_lines = summary["warnings"]
    return "\n".join(
        [
            f"Run summary saved: {summary['output_path']}",
            f"Archive path: {summary['archive_path']}",
            f"Overall status: {summary['overall_status']}",
            f"Top headlines included: {summary['top_headlines_included']}",
            f"Key tickers included: {summary['key_tickers_included']}",
            f"Macro events included: {summary['macro_events_included']}",
            f"Approximate briefing line count: {summary['line_count']}",
            *warning_lines,
        ]
    )


def format_quality_validation_summary(summary: dict[str, Any]) -> str:
    check_lines = [
        f"- {check_name}: {status}"
        for check_name, status in summary["quality_checks"].items()
    ]
    warning_lines = summary["warnings"]
    return "\n".join(
        [
            "Briefing quality validation:",
            f"Run type: {summary['run_type']}",
            f"Briefing path: {summary['briefing_path']}",
            f"Overall status: {summary['overall_status']}",
            f"Top market themes found: {summary['top_headlines_included']}",
            f"Key tickers found: {summary['key_tickers_included']}",
            f"Macro events found: {summary['macro_events_included']}",
            f"Approximate briefing line count: {summary['line_count']}",
            "Quality checks:",
            *check_lines,
            *warning_lines,
        ]
    )
