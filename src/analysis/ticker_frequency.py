import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


INPUT_PATH = Path("data/processed/recent_equity_headlines.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/ticker_frequency.csv")
INPUT_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")
OUTPUT_FIELDS = (
    "ticker",
    "company_or_theme",
    "yahoo_feed_count",
    "inferred_count",
    "total_count",
    "sources",
    "example_headlines",
)

TICKER_THEME_MAP = {
    "AAPL": {
        "company_or_theme": "Apple / iPhone / App Store",
        "keywords": ("apple", "iphone", "app store"),
    },
    "MSFT": {
        "company_or_theme": "Microsoft / OpenAI / Azure",
        "keywords": ("microsoft", "openai", "azure"),
    },
    "NVDA": {
        "company_or_theme": "Nvidia / AI chip / Blackwell",
        "keywords": ("nvidia", "ai chip", "blackwell"),
    },
    "AMZN": {
        "company_or_theme": "Amazon / AWS",
        "keywords": ("amazon", "aws"),
    },
    "GOOGL": {
        "company_or_theme": "Alphabet / Google / YouTube",
        "keywords": ("alphabet", "google", "youtube"),
    },
    "META": {
        "company_or_theme": "Meta / Facebook / Instagram / WhatsApp",
        "keywords": ("meta", "facebook", "instagram", "whatsapp"),
    },
    "TSLA": {
        "company_or_theme": "Tesla / Elon Musk / FSD",
        "keywords": ("tesla", "elon musk", "fsd"),
    },
    "NKE": {
        "company_or_theme": "Nike",
        "keywords": ("nike",),
    },
    "LLY": {
        "company_or_theme": "Eli Lilly / Lilly / GLP-1 / obesity drug",
        "keywords": ("eli lilly", "lilly", "glp-1", "obesity drug", "obesity drugs"),
    },
    "NVO": {
        "company_or_theme": "Novo Nordisk / weight-loss drug",
        "keywords": (
            "novo nordisk",
            "weight-loss drug",
            "weight-loss drugs",
            "weight loss drug",
            "weight loss drugs",
        ),
    },
    "REGN": {
        "company_or_theme": "Regeneron",
        "keywords": ("regeneron",),
    },
    "CMCSA": {
        "company_or_theme": "Comcast / NBCUniversal",
        "keywords": ("comcast", "nbcuniversal", "nbc universal"),
    },
}


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped_term = re.escape(term)
    return re.compile(rf"(?<![A-Za-z0-9]){escaped_term}(?![A-Za-z0-9])", re.IGNORECASE)


MATCH_PATTERNS = {
    ticker: [
        _term_pattern(ticker),
        *[_term_pattern(keyword) for keyword in theme_config["keywords"]],
    ]
    for ticker, theme_config in TICKER_THEME_MAP.items()
}


def read_headline_csv(input_path: Path = INPUT_PATH) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {field: row.get(field, "") for field in INPUT_FIELDS}
            for row in reader
        ]


def save_ticker_frequency_csv(
    records: list[dict[str, str]], output_path: Path = DEFAULT_OUTPUT_PATH
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def infer_tickers_from_headline(record: dict[str, str]) -> set[str]:
    inferred_tickers: set[str] = set()
    headline = record.get("headline", "").strip().lower()

    if not headline:
        return inferred_tickers

    for ticker, patterns in MATCH_PATTERNS.items():
        if any(pattern.search(headline) for pattern in patterns):
            inferred_tickers.add(ticker)

    return inferred_tickers


def should_use_as_example(record: dict[str, str], ticker: str) -> bool:
    headline = record.get("headline", "").strip().lower()
    if not headline:
        return False

    return any(pattern.search(headline) for pattern in MATCH_PATTERNS.get(ticker, []))


def build_ticker_frequency(
    input_records: list[dict[str, str]],
) -> tuple[list[dict[str, str]], int, list[str]]:
    yahoo_feed_counts: dict[str, int] = defaultdict(int)
    inferred_counts: dict[str, int] = defaultdict(int)
    ticker_sources: dict[str, set[str]] = defaultdict(set)
    ticker_examples: dict[str, list[str]] = defaultdict(list)
    rows_with_no_inferred_ticker = 0
    excluded_example_headlines: list[str] = []

    for record in input_records:
        source = record.get("source", "")
        feed_ticker = record.get("ticker", "").strip().upper()
        headline = record.get("headline", "").strip()
        inferred_tickers = infer_tickers_from_headline(record)

        if source == "Yahoo Finance" and feed_ticker:
            yahoo_feed_counts[feed_ticker] += 1
            ticker_sources[feed_ticker].add(source)

            if not should_use_as_example(record, feed_ticker) and headline:
                excluded_example_headlines.append(headline)

        if not inferred_tickers:
            rows_with_no_inferred_ticker += 1

        for ticker in inferred_tickers:
            inferred_counts[ticker] += 1
            ticker_sources[ticker].add(record.get("source", ""))

            if should_use_as_example(record, ticker) and headline not in ticker_examples[ticker]:
                ticker_examples[ticker].append(headline)

    output_records = []
    all_tickers = set(yahoo_feed_counts) | set(inferred_counts)
    for ticker in all_tickers:
        yahoo_feed_count = yahoo_feed_counts[ticker]
        inferred_count = inferred_counts[ticker]
        total_count = yahoo_feed_count + inferred_count
        output_records.append(
            {
                "ticker": ticker,
                "company_or_theme": TICKER_THEME_MAP.get(ticker, {}).get(
                    "company_or_theme", ticker
                ),
                "yahoo_feed_count": str(yahoo_feed_count),
                "inferred_count": str(inferred_count),
                "total_count": str(total_count),
                "sources": "; ".join(sorted(ticker_sources[ticker])),
                "example_headlines": " | ".join(ticker_examples[ticker][:3]),
            }
        )

    output_records.sort(
        key=lambda record: (
            -int(record["inferred_count"]),
            -int(record["total_count"]),
            record["ticker"],
        )
    )
    return output_records, rows_with_no_inferred_ticker, excluded_example_headlines


def build_validation_summary(
    input_records: list[dict[str, str]],
    output_records: list[dict[str, str]],
    rows_with_no_inferred_ticker: int,
    excluded_example_headlines: list[str],
) -> dict[str, Any]:
    top_by_inferred_count = [
        f"{record['ticker']}: {record['inferred_count']}"
        for record in sorted(
            output_records,
            key=lambda record: (
                -int(record["inferred_count"]),
                -int(record["total_count"]),
                record["ticker"],
            ),
        )[:10]
    ]
    top_by_total_count = [
        f"{record['ticker']}: {record['total_count']}"
        for record in sorted(
            output_records,
            key=lambda record: (
                -int(record["total_count"]),
                -int(record["inferred_count"]),
                record["ticker"],
            ),
        )[:10]
    ]

    return {
        "input_rows": len(input_records),
        "tickers_found": len(output_records),
        "top_by_inferred_count": top_by_inferred_count,
        "top_by_total_count": top_by_total_count,
        "rows_with_no_inferred_ticker": rows_with_no_inferred_ticker,
        "excluded_example_headlines": excluded_example_headlines[:5],
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    top_inferred_lines = [
        f"  {index}. {ticker_summary}"
        for index, ticker_summary in enumerate(
            summary["top_by_inferred_count"], start=1
        )
    ]
    top_total_lines = [
        f"  {index}. {ticker_summary}"
        for index, ticker_summary in enumerate(summary["top_by_total_count"], start=1)
    ]
    excluded_example_lines = [
        f"  {index}. {headline}"
        for index, headline in enumerate(
            summary["excluded_example_headlines"], start=1
        )
    ]

    return "\n".join(
        [
            "Ticker frequency validation summary:",
            f"Input rows: {summary['input_rows']}",
            f"Number of tickers found: {summary['tickers_found']}",
            "Top 10 tickers by inferred_count:",
            *top_inferred_lines,
            "Top 10 tickers by total_count:",
            *top_total_lines,
            (
                "Rows with no detected inferred ticker/theme: "
                f"{summary['rows_with_no_inferred_ticker']}"
            ),
            (
                "Examples excluded from ticker examples because the headline did not "
                "directly mention the ticker/company/theme:"
            ),
            *excluded_example_lines,
        ]
    )


def count_ticker_frequency(
    input_path: Path = INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    input_records = read_headline_csv(input_path=input_path)
    (
        output_records,
        rows_with_no_inferred_ticker,
        excluded_example_headlines,
    ) = build_ticker_frequency(input_records)
    saved_path = save_ticker_frequency_csv(
        records=output_records,
        output_path=output_path,
    )
    summary = build_validation_summary(
        input_records=input_records,
        output_records=output_records,
        rows_with_no_inferred_ticker=rows_with_no_inferred_ticker,
        excluded_example_headlines=excluded_example_headlines,
    )
    return output_records, saved_path, summary
