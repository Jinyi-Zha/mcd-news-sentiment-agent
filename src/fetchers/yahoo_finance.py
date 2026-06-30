import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yfinance as yf


DEFAULT_TICKERS = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA")
DEFAULT_OUTPUT_PATH = Path("data/raw/yahoo_headlines.csv")
CSV_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")


def _timestamp_from_item(item: dict[str, Any]) -> str:
    raw_timestamp = item.get("providerPublishTime") or item.get("pubDate")

    if isinstance(raw_timestamp, (int, float)):
        return datetime.fromtimestamp(raw_timestamp, tz=timezone.utc).isoformat()

    if isinstance(raw_timestamp, str):
        return raw_timestamp

    content = item.get("content")
    if isinstance(content, dict):
        content_timestamp = content.get("pubDate") or content.get("displayTime")
        if isinstance(content_timestamp, str):
            return content_timestamp

    return ""


def _headline_from_item(item: dict[str, Any]) -> str:
    headline = item.get("title")
    if isinstance(headline, str):
        return headline

    content = item.get("content")
    if isinstance(content, dict):
        content_headline = content.get("title")
        if isinstance(content_headline, str):
            return content_headline

    return ""


def _publisher_from_item(item: dict[str, Any]) -> str:
    publisher = item.get("publisher")
    if isinstance(publisher, str):
        return publisher

    content = item.get("content")
    if isinstance(content, dict):
        provider = content.get("provider")
        if isinstance(provider, dict) and isinstance(provider.get("displayName"), str):
            return provider["displayName"]

        content_provider = content.get("providerName")
        if isinstance(content_provider, str):
            return content_provider

    return ""


def _url_from_item(item: dict[str, Any]) -> str:
    url = item.get("link")
    if isinstance(url, str):
        return url

    content = item.get("content")
    if isinstance(content, dict):
        canonical_url = content.get("canonicalUrl")
        if isinstance(canonical_url, dict) and isinstance(canonical_url.get("url"), str):
            return canonical_url["url"]

        click_url = content.get("clickThroughUrl")
        if isinstance(click_url, dict) and isinstance(click_url.get("url"), str):
            return click_url["url"]

    return ""


def normalize_news_item(ticker: str, item: dict[str, Any]) -> dict[str, str]:
    return {
        "source": "Yahoo Finance",
        "ticker": ticker,
        "headline": _headline_from_item(item),
        "publisher": _publisher_from_item(item),
        "timestamp": _timestamp_from_item(item),
        "url": _url_from_item(item),
    }


def fetch_yahoo_headlines(tickers: tuple[str, ...] = DEFAULT_TICKERS) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []

    for ticker in tickers:
        news_items = yf.Ticker(ticker).news or []
        for item in news_items:
            if not isinstance(item, dict):
                continue

            record = normalize_news_item(ticker, item)
            if record["headline"]:
                records.append(record)

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
    rows_per_ticker = Counter(record.get("ticker", "") for record in records)
    missing_ticker_rows = rows_per_ticker.get("", 0)

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
        "rows_per_ticker": dict(rows_per_ticker),
        "missing_ticker_rows": missing_ticker_rows,
        "duplicate_headlines": duplicate_headlines,
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    rows_per_ticker = summary["rows_per_ticker"]
    ticker_lines = [
        f"  {ticker}: {rows_per_ticker.get(ticker, 0)}"
        for ticker in DEFAULT_TICKERS
    ]

    return "\n".join(
        [
            "Yahoo pull validation summary:",
            f"Total rows: {summary['total_rows']}",
            "Rows per ticker:",
            *ticker_lines,
            f"Rows with missing ticker: {summary['missing_ticker_rows']}",
            f"Duplicate headlines: {summary['duplicate_headlines']}",
            (
                "Timestamp range: "
                f"{summary['earliest_timestamp']} to {summary['latest_timestamp']}"
                if summary["earliest_timestamp"] and summary["latest_timestamp"]
                else "Timestamp range: unavailable"
            ),
        ]
    )


def pull_and_save_yahoo_headlines(
    tickers: tuple[str, ...] = DEFAULT_TICKERS,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    records = fetch_yahoo_headlines(tickers=tickers)
    saved_path = save_headlines_csv(records=records, output_path=output_path)
    summary = build_validation_summary(records)
    return records, saved_path, summary
