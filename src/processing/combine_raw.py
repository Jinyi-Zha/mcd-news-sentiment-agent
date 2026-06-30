import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


YAHOO_RAW_PATH = Path("data/raw/yahoo_headlines.csv")
CNBC_RAW_PATH = Path("data/raw/cnbc_headlines.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/combined_raw_headlines.csv")
CSV_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")


def read_headline_csv(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {field: row.get(field, "") for field in CSV_FIELDS}
            for row in reader
        ]


def save_combined_csv(
    records: list[dict[str, str]], output_path: Path = DEFAULT_OUTPUT_PATH
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def _parse_timestamp(timestamp: str) -> datetime | None:
    if not timestamp:
        return None

    normalized_timestamp = timestamp.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalized_timestamp)
    except ValueError:
        return None


def build_validation_summary(records: list[dict[str, str]]) -> dict[str, Any]:
    rows_by_source = Counter(record.get("source", "") for record in records)
    missing_ticker_rows = sum(
        1 for record in records if not record.get("ticker", "").strip()
    )
    missing_headline_rows = sum(
        1 for record in records if not record.get("headline", "").strip()
    )

    headline_counts = Counter(
        record.get("headline", "").strip().lower()
        for record in records
        if record.get("headline", "").strip()
    )
    duplicate_headlines = sum(
        count - 1 for count in headline_counts.values() if count > 1
    )

    parsed_timestamps = [
        (parsed_timestamp, record["timestamp"])
        for record in records
        if record.get("timestamp")
        for parsed_timestamp in [_parse_timestamp(record["timestamp"])]
        if parsed_timestamp is not None
    ]

    earliest_timestamp = ""
    latest_timestamp = ""
    if parsed_timestamps:
        earliest_timestamp = min(parsed_timestamps, key=lambda item: item[0])[1]
        latest_timestamp = max(parsed_timestamps, key=lambda item: item[0])[1]

    return {
        "total_rows": len(records),
        "rows_by_source": dict(rows_by_source),
        "missing_ticker_rows": missing_ticker_rows,
        "missing_headline_rows": missing_headline_rows,
        "duplicate_headlines": duplicate_headlines,
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    source_lines = [
        f"  {source}: {count}"
        for source, count in sorted(summary["rows_by_source"].items())
    ]

    return "\n".join(
        [
            "Combined raw headlines validation summary:",
            f"Total rows: {summary['total_rows']}",
            "Rows by source:",
            *source_lines,
            f"Rows with missing ticker: {summary['missing_ticker_rows']}",
            f"Rows with missing headline: {summary['missing_headline_rows']}",
            f"Duplicate headlines: {summary['duplicate_headlines']}",
            (
                "Timestamp range: "
                f"{summary['earliest_timestamp']} to {summary['latest_timestamp']}"
                if summary["earliest_timestamp"] and summary["latest_timestamp"]
                else "Timestamp range: unavailable"
            ),
        ]
    )


def combine_raw_headlines(
    yahoo_path: Path = YAHOO_RAW_PATH,
    cnbc_path: Path = CNBC_RAW_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    records = [
        *read_headline_csv(yahoo_path),
        *read_headline_csv(cnbc_path),
    ]
    saved_path = save_combined_csv(records=records, output_path=output_path)
    summary = build_validation_summary(records)
    return records, saved_path, summary

