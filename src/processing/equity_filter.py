import csv
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


INPUT_PATH = Path("data/processed/combined_raw_headlines.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/filtered_equity_headlines.csv")
CSV_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")

COMPANY_OR_TICKER_TERMS = (
    "aapl",
    "apple",
    "msft",
    "microsoft",
    "nvda",
    "nvidia",
    "amzn",
    "amazon",
    "googl",
    "alphabet",
    "google",
    "meta",
    "tsla",
    "tesla",
    "nike",
    "eli lilly",
    "regeneron",
    "comcast",
    "nbcuniversal",
    "kohl",
    "walmart",
    "gm",
    "general motors",
    "jpmorgan",
    "goldman sachs",
    "toyota",
    "slate auto",
    "target",
    "lucid",
    "disney",
    "aerovironment",
    "databricks",
    "lululemon",
    "crowdstrike",
)
EQUITY_TERMS = (
    "stock",
    "stocks",
    "share",
    "shares",
    "equity",
    "equities",
    "earnings",
    "revenue",
    "guidance",
    "ipo",
    "m&a",
    "merger",
    "acquisition",
    "buyout",
    "analyst",
    "rating",
    "upgrade",
    "downgrade",
    "price target",
)
SECTOR_TERMS = (
    "tech",
    "technology",
    "banks",
    "bank",
    "banking",
    "semiconductor",
    "semiconductors",
    "chip",
    "chips",
    "energy",
    "healthcare",
    "health care",
    "pharma",
    "retail",
    "auto",
    "automotive",
    "electric vehicle",
    "ev",
    "media",
    "entertainment",
    "advertising",
    "luxury",
    "consumer",
    "defense",
    "aerospace",
    "drone",
    "dronemaker",
    "shipping",
    "manufacturing",
)
INDEX_TERMS = (
    "s&p 500",
    "sp 500",
    "nasdaq",
    "dow",
    "wall street",
    "stock market",
)
THEME_TO_TICKER_TERMS = (
    "obesity drug",
    "glp-1",
    "weight-loss drug",
    "weight loss drug",
    "medicare drug coverage",
    "tiktok",
    "youtube",
    "instagram",
    "whatsapp",
)
EXCLUDE_ONLY_TERMS = (
    "bitcoin",
    "crypto",
    "cryptocurrency",
    "ethereum",
    "dollar",
    "euro",
    "yen",
    "pound",
    "currency",
    "currencies",
    "forex",
    "fx",
    "bond",
    "bonds",
    "treasury",
    "treasuries",
    "yield",
    "yields",
    "rates",
    "oil",
    "crude",
    "gold",
    "silver",
    "copper",
    "natural gas",
    "commodity",
    "commodities",
)


def read_headline_csv(input_path: Path = INPUT_PATH) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {field: row.get(field, "") for field in CSV_FIELDS}
            for row in reader
        ]


def save_filtered_csv(
    records: list[dict[str, str]], output_path: Path = DEFAULT_OUTPUT_PATH
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def is_equity_relevant(record: dict[str, str]) -> bool:
    headline = record.get("headline", "").strip().lower()
    ticker = record.get("ticker", "").strip()

    if not headline:
        return False

    has_equity_signal = (
        bool(ticker)
        or _contains_any(headline, COMPANY_OR_TICKER_TERMS)
        or _contains_any(headline, EQUITY_TERMS)
        or _contains_any(headline, SECTOR_TERMS)
        or _contains_any(headline, INDEX_TERMS)
        or _contains_any(headline, THEME_TO_TICKER_TERMS)
    )

    if has_equity_signal:
        return True

    if _contains_any(headline, EXCLUDE_ONLY_TERMS):
        return False

    return False


def split_equity_headlines(
    records: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    kept_records: list[dict[str, str]] = []
    removed_records: list[dict[str, str]] = []

    for record in records:
        if is_equity_relevant(record):
            kept_records.append(record)
        else:
            removed_records.append(record)

    return kept_records, removed_records


def _parse_timestamp(timestamp: str) -> datetime | None:
    if not timestamp:
        return None

    normalized_timestamp = timestamp.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalized_timestamp)
    except ValueError:
        return None


def build_validation_summary(
    input_records: list[dict[str, str]],
    kept_records: list[dict[str, str]],
    removed_records: list[dict[str, str]],
) -> dict[str, Any]:
    kept_by_source = Counter(record.get("source", "") for record in kept_records)
    parsed_timestamps = [
        (parsed_timestamp, record["timestamp"])
        for record in kept_records
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
        "input_rows": len(input_records),
        "output_rows": len(kept_records),
        "removed_rows": len(removed_records),
        "kept_by_source": dict(kept_by_source),
        "kept_examples": [record["headline"] for record in kept_records[:5]],
        "removed_examples": [record["headline"] for record in removed_records[:5]],
        "earliest_timestamp": earliest_timestamp,
        "latest_timestamp": latest_timestamp,
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    source_lines = [
        f"  {source}: {count}"
        for source, count in sorted(summary["kept_by_source"].items())
    ]
    kept_example_lines = [
        f"  {index}. {headline}"
        for index, headline in enumerate(summary["kept_examples"], start=1)
    ]
    removed_example_lines = [
        f"  {index}. {headline}"
        for index, headline in enumerate(summary["removed_examples"], start=1)
    ]

    return "\n".join(
        [
            "Equity filter validation summary:",
            f"Input rows: {summary['input_rows']}",
            f"Output rows: {summary['output_rows']}",
            f"Rows removed: {summary['removed_rows']}",
            "Rows kept by source:",
            *source_lines,
            (
                "Timestamp range: "
                f"{summary['earliest_timestamp']} to {summary['latest_timestamp']}"
                if summary["earliest_timestamp"] and summary["latest_timestamp"]
                else "Timestamp range: unavailable"
            ),
            "Examples of kept headlines:",
            *kept_example_lines,
            "Examples of removed headlines:",
            *removed_example_lines,
        ]
    )


def filter_equity_headlines(
    input_path: Path = INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any], list[dict[str, str]]]:
    input_records = read_headline_csv(input_path=input_path)
    kept_records, removed_records = split_equity_headlines(input_records)
    saved_path = save_filtered_csv(records=kept_records, output_path=output_path)
    summary = build_validation_summary(
        input_records=input_records,
        kept_records=kept_records,
        removed_records=removed_records,
    )
    return kept_records, saved_path, summary, removed_records
