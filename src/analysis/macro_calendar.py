import csv
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from datetime import datetime


DEFAULT_OUTPUT_PATH = Path("data/processed/macro_calendar.csv")
DEFAULT_CONFIG_PATH = Path("config/macro_calendar_2026.csv")
CONFIG_FIELDS = (
    "date",
    "time_london",
    "country",
    "event",
    "importance",
    "asset_impact",
)
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

FALLBACK_MACRO_CALENDAR = (
    {
        "date": "2026-07-01",
        "time_london": "09:30",
        "event": "UK Manufacturing PMI final",
        "region": "UK",
        "importance": "medium",
        "expected": "",
        "prior": "",
        "source": "Manual fallback calendar",
    },
    {
        "date": "2026-07-01",
        "time_london": "14:45",
        "event": "US S&P Global Manufacturing PMI final",
        "region": "US",
        "importance": "medium",
        "expected": "",
        "prior": "",
        "source": "Manual fallback calendar",
    },
    {
        "date": "2026-07-01",
        "time_london": "15:00",
        "event": "US ISM Manufacturing PMI",
        "region": "US",
        "importance": "high",
        "expected": "",
        "prior": "",
        "source": "Manual fallback calendar",
    },
    {
        "date": "2026-07-03",
        "time_london": "13:30",
        "event": "US Nonfarm Payrolls / NFP",
        "region": "US",
        "importance": "high",
        "expected": "",
        "prior": "",
        "source": "Manual fallback calendar",
    },
    {
        "date": "2026-07-03",
        "time_london": "13:30",
        "event": "US Unemployment Rate",
        "region": "US",
        "importance": "high",
        "expected": "",
        "prior": "",
        "source": "Manual fallback calendar",
    },
)


def london_today() -> str:
    return datetime.now(LONDON_TZ).date().isoformat()


def normalize_config_record(record: dict[str, str], config_path: Path) -> dict[str, str]:
    return {
        "date": record.get("date", "").strip(),
        "time_london": record.get("time_london", "").strip(),
        "event": record.get("event", "").strip(),
        "region": record.get("country", "").strip(),
        "importance": record.get("importance", "").strip(),
        "expected": "",
        "prior": "",
        "source": str(config_path),
    }


def load_config_events(config_path: Path = DEFAULT_CONFIG_PATH) -> list[dict[str, str]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Macro calendar config not found: {config_path}")

    with config_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames is None:
            raise ValueError(f"Macro calendar config is empty: {config_path}")

        missing_fields = set(CONFIG_FIELDS) - set(reader.fieldnames)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"Macro calendar config missing columns: {missing}")

        records = [normalize_config_record(record, config_path) for record in reader]

    records = [
        record
        for record in records
        if record["date"] and record["time_london"] and record["event"]
    ]
    if not records:
        raise ValueError(f"Macro calendar config has no usable rows: {config_path}")

    return records


def fallback_events_for_date(target_date: str) -> list[dict[str, str]]:
    return [
        {field: event.get(field, "") for field in OUTPUT_FIELDS}
        for event in FALLBACK_MACRO_CALENDAR
        if event["date"] == target_date
    ]


def events_for_date(
    target_date: str,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> tuple[list[dict[str, str]], str, bool, str]:
    try:
        all_events = load_config_events(config_path=config_path)
        records = [
            {field: event.get(field, "") for field in OUTPUT_FIELDS}
            for event in all_events
            if event["date"] == target_date
        ]
        return records, str(config_path), False, ""
    except (csv.Error, FileNotFoundError, ValueError) as error:
        records = fallback_events_for_date(target_date)
        return records, "Manual fallback calendar", True, str(error)


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
    calendar_source: str,
    fallback_used: bool,
    fallback_reason: str,
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
        "calendar_source": calendar_source,
        "fallback_used": fallback_used,
        "fallback_reason": fallback_reason,
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
        f"Calendar source: {summary['calendar_source']}",
        f"Fallback used: {summary['fallback_used']}",
        "High importance events:",
    ]

    if high_importance_lines:
        lines.extend(high_importance_lines)
    else:
        lines.append("  None")

    lines.append(f"Output path: {summary['output_path']}")
    if summary["fallback_reason"]:
        lines.append(f"Fallback reason: {summary['fallback_reason']}")
    return "\n".join(lines)


def build_macro_calendar(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    target_date: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    resolved_target_date = target_date or london_today()
    records, calendar_source, fallback_used, fallback_reason = events_for_date(
        target_date=resolved_target_date,
        config_path=config_path,
    )
    saved_path = save_macro_calendar_csv(records=records, output_path=output_path)
    summary = build_validation_summary(
        target_date=resolved_target_date,
        records=records,
        output_path=saved_path,
        calendar_source=calendar_source,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )
    return records, saved_path, summary
