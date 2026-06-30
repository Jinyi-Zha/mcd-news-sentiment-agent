import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


INPUT_PATH = Path("data/processed/filtered_equity_headlines.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/recent_equity_headlines.csv")
CSV_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")
DEFAULT_LOOKBACK_HOURS = {
    "eu_open": 12.0,
    "us_open": 8.0,
    "us_close": 8.0,
}
LONDON_TZ = ZoneInfo("Europe/London")


def read_headline_csv(input_path: Path = INPUT_PATH) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {field: row.get(field, "") for field in CSV_FIELDS}
            for row in reader
        ]


def save_recent_csv(
    records: list[dict[str, str]], output_path: Path = DEFAULT_OUTPUT_PATH
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def get_lookback_hours(run_type: str, lookback_hours: float | None = None) -> float:
    if lookback_hours is not None:
        return lookback_hours

    return DEFAULT_LOOKBACK_HOURS[run_type]


def parse_timestamp(timestamp: str) -> datetime | None:
    if not timestamp:
        return None

    normalized_timestamp = timestamp.strip().replace("Z", "+00:00")

    try:
        parsed_timestamp = datetime.fromisoformat(normalized_timestamp)
    except ValueError:
        return None

    if parsed_timestamp.tzinfo is None:
        return parsed_timestamp.replace(tzinfo=timezone.utc)

    return parsed_timestamp


def split_recent_headlines(
    records: list[dict[str, str]],
    reference_london_time: datetime,
    lookback_hours: float,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    cutoff_time = reference_london_time - timedelta(hours=lookback_hours)
    recent_records: list[dict[str, str]] = []
    too_old_records: list[dict[str, str]] = []
    unparseable_records: list[dict[str, str]] = []

    for record in records:
        parsed_timestamp = parse_timestamp(record.get("timestamp", ""))
        if parsed_timestamp is None:
            unparseable_records.append(record)
            continue

        london_timestamp = parsed_timestamp.astimezone(LONDON_TZ)
        if london_timestamp >= cutoff_time:
            recent_records.append(record)
        else:
            too_old_records.append(record)

    return recent_records, too_old_records, unparseable_records


def build_validation_summary(
    input_records: list[dict[str, str]],
    recent_records: list[dict[str, str]],
    too_old_records: list[dict[str, str]],
    unparseable_records: list[dict[str, str]],
    lookback_hours: float,
    reference_london_time: datetime,
) -> dict[str, Any]:
    rows_by_source = Counter(record.get("source", "") for record in recent_records)
    parsed_timestamps = [
        (parsed_timestamp, record["timestamp"])
        for record in recent_records
        if record.get("timestamp")
        for parsed_timestamp in [parse_timestamp(record["timestamp"])]
        if parsed_timestamp is not None
    ]

    earliest_timestamp = ""
    latest_timestamp = ""
    if parsed_timestamps:
        earliest_timestamp = min(parsed_timestamps, key=lambda item: item[0])[1]
        latest_timestamp = max(parsed_timestamps, key=lambda item: item[0])[1]

    return {
        "input_rows": len(input_records),
        "output_rows": len(recent_records),
        "too_old_rows": len(too_old_records),
        "unparseable_timestamp_rows": len(unparseable_records),
        "lookback_hours": lookback_hours,
        "reference_london_time": reference_london_time.isoformat(),
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
        "rows_by_source": dict(rows_by_source),
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    source_lines = [
        f"  {source}: {count}"
        for source, count in sorted(summary["rows_by_source"].items())
    ]

    return "\n".join(
        [
            "Recent equity headlines validation summary:",
            f"Input rows: {summary['input_rows']}",
            f"Output rows: {summary['output_rows']}",
            f"Rows removed for being too old: {summary['too_old_rows']}",
            (
                "Rows removed for unparseable timestamp: "
                f"{summary['unparseable_timestamp_rows']}"
            ),
            f"Lookback hours used: {summary['lookback_hours']:g}",
            f"Reference London time: {summary['reference_london_time']}",
            (
                "Output timestamp range: "
                f"{summary['earliest_timestamp']} to {summary['latest_timestamp']}"
                if summary["earliest_timestamp"] and summary["latest_timestamp"]
                else "Output timestamp range: unavailable"
            ),
            "Rows kept by source:",
            *source_lines,
        ]
    )


def filter_recent_headlines(
    run_type: str,
    lookback_hours: float | None = None,
    input_path: Path = INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    reference_london_time: datetime | None = None,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    input_records = read_headline_csv(input_path=input_path)
    resolved_lookback_hours = get_lookback_hours(
        run_type=run_type,
        lookback_hours=lookback_hours,
    )
    resolved_reference_time = reference_london_time or datetime.now(LONDON_TZ)

    recent_records, too_old_records, unparseable_records = split_recent_headlines(
        records=input_records,
        reference_london_time=resolved_reference_time,
        lookback_hours=resolved_lookback_hours,
    )
    saved_path = save_recent_csv(records=recent_records, output_path=output_path)
    summary = build_validation_summary(
        input_records=input_records,
        recent_records=recent_records,
        too_old_records=too_old_records,
        unparseable_records=unparseable_records,
        lookback_hours=resolved_lookback_hours,
        reference_london_time=resolved_reference_time,
    )
    return recent_records, saved_path, summary

