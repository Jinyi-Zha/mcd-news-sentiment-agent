import csv
from collections import Counter
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import feedparser


CNBC_RSS_FEEDS = (
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",
)
DEFAULT_OUTPUT_PATH = Path("data/raw/cnbc_headlines.csv")
CSV_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")


def _timestamp_from_entry(entry: dict[str, Any]) -> str:
    raw_timestamp = entry.get("published") or entry.get("updated")
    if not isinstance(raw_timestamp, str):
        return ""

    try:
        return parsedate_to_datetime(raw_timestamp).isoformat()
    except (TypeError, ValueError):
        return raw_timestamp


def normalize_rss_entry(entry: dict[str, Any]) -> dict[str, str]:
    headline = entry.get("title", "")
    url = entry.get("link", "")

    return {
        "source": "CNBC RSS",
        "ticker": "",
        "headline": headline if isinstance(headline, str) else "",
        "publisher": "CNBC",
        "timestamp": _timestamp_from_entry(entry),
        "url": url if isinstance(url, str) else "",
    }


def fetch_cnbc_headlines(
    feed_urls: tuple[str, ...] = CNBC_RSS_FEEDS,
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []

    for feed_url in feed_urls:
        parsed_feed = feedparser.parse(feed_url)
        for entry in parsed_feed.entries:
            records.append(normalize_rss_entry(entry))

    return records


def save_headlines_csv(
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
        "missing_headline_rows": missing_headline_rows,
        "duplicate_headlines": duplicate_headlines,
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "CNBC RSS pull validation summary:",
            f"Total rows: {summary['total_rows']}",
            f"Rows with missing headline: {summary['missing_headline_rows']}",
            (
                "Timestamp range: "
                f"{summary['earliest_timestamp']} to {summary['latest_timestamp']}"
                if summary["earliest_timestamp"] and summary["latest_timestamp"]
                else "Timestamp range: unavailable"
            ),
            f"Duplicate headlines: {summary['duplicate_headlines']}",
        ]
    )


def pull_and_save_cnbc_headlines(
    feed_urls: tuple[str, ...] = CNBC_RSS_FEEDS,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    records = fetch_cnbc_headlines(feed_urls=feed_urls)
    saved_path = save_headlines_csv(records=records, output_path=output_path)
    summary = build_validation_summary(records)
    return records, saved_path, summary

