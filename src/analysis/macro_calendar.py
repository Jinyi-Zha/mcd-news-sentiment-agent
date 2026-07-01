import csv
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from datetime import datetime


DEFAULT_OUTPUT_PATH = Path("data/processed/macro_calendar.csv")
OUTPUT_FIELDS = (
    "date",
    "time_london",
    "event",
    "region",
    "importance",
    "expected",
    "prior",
    "source",
)
LONDON_TZ = ZoneInfo("Europe/London")

MANUAL_MACRO_CALENDAR = (
    {
        "date": "2026-07-01",
        "time_london": "09:30",
        "event": "UK Manufacturing PMI final",
        "region": "UK",
        "importance": "medium",
        "expected": "",
        "prior": "",
        "source": "Manual v1 calendar",
    },
    {
        "date": "2026-07-01",
        "time_london": "14:45",
        "event": "US S&P Global Manufacturing PMI final",
        "region": "US",
        "importance": "medium",
        "expected": "",
        "prior": "",
        "source": "Manual v1 calendar",
    },
    {
        "date": "2026-07-01",
        "time_london": "15:00",
        "event": "US ISM Manufacturing PMI",
        "region": "US",
        "importance": "high",
        "expected": "",
        "prior": "",
        "source": "Manual v1 calendar",
    },
    {
        "date": "2026-07-03",
        "time_london": "13:30",
        "event": "US Nonfarm Payrolls / NFP",
        "region": "US",
        "importance": "high",
        "expected": "",
        "prior": "",
        "source": "Manual v1 calendar",
    },
    {
        "date": "2026-07-03",
        "time_london": "13:30",
        "event": "US Unemployment Rate",
        "region": "US",
        "importance": "high",
        "expected": "",
        "prior": "",
        "source": "Manual v1 calendar",
    },
)


def london_today() -> str:
    return datetime.now(LONDON_TZ).date().isoformat()


def events_for_date(target_date: str) -> list[dict[str, str]]:
    return [
        {field: event.get(field, "") for field in OUTPUT_FIELDS}
        for event in MANUAL_MACRO_CALENDAR
        if event["date"] == target_date
    ]


def save_macro_calendar_csv(
    records: list[dict[str, str]], output_path: Path = DEFAULT_OUTPUT_PATH
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def build_validation_summary(
    target_date: str,
    records: list[dict[str, str]],
    output_path: Path,
) -> dict[str, Any]:
    high_importance_events = [
        record["event"]
        for record in records
        if record.get("importance", "").lower() == "high"
    ]

    return {
        "today_london_date": target_date,
        "events_found": len(records),
        "high_importance_events": high_importance_events,
        "output_path": str(output_path),
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    high_importance_lines = [
        f"  {index}. {event}"
        for index, event in enumerate(summary["high_importance_events"], start=1)
    ]

    lines = [
        "Macro calendar validation summary:",
        f"Today's London date: {summary['today_london_date']}",
        f"Number of events found: {summary['events_found']}",
        "High importance events:",
    ]

    if high_importance_lines:
        lines.extend(high_importance_lines)
    else:
        lines.append("  None")

    lines.append(f"Output path: {summary['output_path']}")
    return "\n".join(lines)


def build_macro_calendar(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    target_date: str | None = None,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    resolved_target_date = target_date or london_today()
    records = events_for_date(resolved_target_date)
    saved_path = save_macro_calendar_csv(records=records, output_path=output_path)
    summary = build_validation_summary(
        target_date=resolved_target_date,
        records=records,
        output_path=saved_path,
    )
    return records, saved_path, summary

