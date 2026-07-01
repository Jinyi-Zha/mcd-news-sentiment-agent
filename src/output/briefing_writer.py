import csv
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


REPEATED_HEADLINES_PATH = Path("data/processed/repeated_headlines.csv")
TICKER_FREQUENCY_PATH = Path("data/processed/ticker_frequency.csv")
MACRO_CALENDAR_PATH = Path("data/processed/macro_calendar.csv")
OUTPUT_DIR = Path("outputs")
LONDON_TZ = ZoneInfo("Europe/London")
RUN_TYPE_LABELS = {
    "eu_open": "EU Open",
    "us_open": "US Open",
    "us_close": "US Close",
}


def read_csv_records(input_path: Path) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def first_example(example_headlines: str) -> str:
    examples = [example.strip() for example in example_headlines.split("|")]
    return next((example for example in examples if example), "")


def top_headlines(records: list[dict[str, str]], limit: int = 4) -> list[dict[str, str]]:
    eligible_records = [
        record
        for record in records
        if record.get("briefing_eligible", "").lower() == "true"
    ]
    eligible_records.sort(
        key=lambda record: (
            -int(record.get("source_count", "0")),
            -int(record.get("headline_count", "0")),
            record.get("story_label", ""),
        )
    )

    selected_records: list[dict[str, str]] = []
    seen_representative_headlines: set[str] = set()
    for record in eligible_records:
        representative = record.get("representative_headline", "").strip()
        if representative in seen_representative_headlines:
            continue

        selected_records.append(record)
        seen_representative_headlines.add(representative)
        if len(selected_records) == limit:
            break

    return selected_records


def key_tickers(records: list[dict[str, str]], limit: int = 4) -> list[dict[str, str]]:
    sorted_records = sorted(
        records,
        key=lambda record: (
            -int(record.get("inferred_count", "0")),
            -int(record.get("total_count", "0")),
            record.get("ticker", ""),
        ),
    )
    return sorted_records[:limit]


def macro_events(records: list[dict[str, str]], limit: int = 5) -> list[dict[str, str]]:
    sorted_records = sorted(
        records,
        key=lambda record: (
            record.get("time_london", ""),
            record.get("event", ""),
        ),
    )
    return sorted_records[:limit]


def market_relevance(record: dict[str, str]) -> str:
    label = record.get("story_label", "").lower()

    if "tesla" in label:
        return "Autonomy and deliveries keep high-beta EV sentiment in focus."
    if "microsoft" in label or "openai" in label or "azure" in label:
        return "AI and cloud narratives keep mega-cap tech in focus."
    if "magnificent" in label or "big tech" in label:
        return "Mega-cap tech breadth remains central to index direction."
    if "ipo" in label or "m&a" in label or "deal" in label:
        return "Deal flow may influence risk appetite and single-stock catalysts."
    if "alphabet" in label or "google" in label:
        return "Search, YouTube and AI coverage keep communication services in focus."
    if "apple" in label:
        return "iPhone and App Store coverage keeps consumer tech in focus."
    if "amazon" in label or "aws" in label:
        return "AWS headlines keep AI infrastructure spending in focus."
    if "meta" in label:
        return "Social platforms keep digital advertising exposure in focus."
    if "nvidia" in label or "semiconductor" in label:
        return "Chip coverage could affect semiconductor leadership."

    return "Repeated cross-source coverage marks this as an equity-market focus."


def ticker_focus_reason(record: dict[str, str]) -> str:
    ticker = record.get("ticker", "")
    company_or_theme = record.get("company_or_theme", "")
    reason_by_ticker = {
        "AAPL": "iPhone, App Store and regulatory coverage.",
        "MSFT": "AI/platform spending narrative.",
        "NVDA": "AI chip and semiconductor leadership coverage.",
        "AMZN": "AWS and AI infrastructure spending.",
        "GOOGL": "Search, YouTube and AI-platform coverage.",
        "META": "Social platforms and digital advertising.",
        "TSLA": "Autonomy, FSD and delivery headlines.",
        "NKE": "Earnings-related coverage.",
        "LLY": "GLP-1 and obesity-drug coverage.",
        "NVO": "Weight-loss drug headlines.",
        "REGN": "Healthcare and drug-development coverage.",
        "CMCSA": "Media and NBCUniversal headlines.",
    }
    return reason_by_ticker.get(
        ticker,
        f"{company_or_theme} headline flow.",
    )


def executive_summary(repeated_headlines: list[dict[str, str]]) -> list[str]:
    summary_lines = []
    for record in repeated_headlines[:3]:
        summary_lines.append(
            (
                f"- {record['story_label']} remains in focus: "
                f"{record['source_count']} sources / {record['headline_count']} headlines. "
                f"{market_relevance(record)}"
            )
        )

    return summary_lines


def next_watch_points(
    repeated_headlines: list[dict[str, str]],
    ticker_records: list[dict[str, str]],
    macro_records: list[dict[str, str]],
) -> list[str]:
    watch_points = []

    if repeated_headlines:
        top_theme = repeated_headlines[0]
        watch_points.append(
            f"- Top theme: watch whether {top_theme['story_label']} broadens or fades."
        )

    if ticker_records:
        tickers = ", ".join(record["ticker"] for record in ticker_records[:3])
        watch_points.append(
            f"- Key tickers: watch follow-through in {tickers}."
        )

    high_importance_events = [
        record["event"]
        for record in macro_records
        if record.get("importance", "").lower() == "high"
    ]
    if high_importance_events:
        watch_points.append(
            f"- Macro: {', '.join(high_importance_events[:2])} may move rates, FX, futures and sectors."
        )
    else:
        watch_points.append(
            "- Macro: light calendar; equity themes may drive the session."
        )

    return watch_points[:3]


def render_briefing(
    run_type: str,
    repeated_headlines: list[dict[str, str]],
    ticker_records: list[dict[str, str]],
    macro_records: list[dict[str, str]],
    london_now: datetime,
) -> str:
    run_label = RUN_TYPE_LABELS[run_type]
    lines = [
        f"MCD Capital — Equities Briefing | {run_label} | {london_now:%Y-%m-%d %H:%M %Z}",
        "",
        "EXECUTIVE SUMMARY",
        *executive_summary(repeated_headlines),
        "",
        "TOP MARKET THEMES",
    ]

    for index, record in enumerate(repeated_headlines, start=1):
        lines.extend(
            [
                f"{index}. Theme: {record['story_label']}",
                f"   Tickers: {record['related_tickers'] or 'N/A'}",
                (
                    f"   Evidence: {record['source_count']} sources / "
                    f"{record['headline_count']} headlines"
                ),
                f"   Rep: {record['representative_headline']}",
                f"   Relevance: {market_relevance(record)}",
            ]
        )

    lines.extend(["", "KEY TICKERS TO WATCH"])
    for index, record in enumerate(ticker_records, start=1):
        lines.extend(
            [
                (
                    f"{index}. {record['ticker']} — {record['company_or_theme']} — "
                    f"inferred {record['inferred_count']} / Yahoo feed "
                    f"{record['yahoo_feed_count']}"
                ),
                f"   Why watch: {ticker_focus_reason(record)}",
            ]
        )

    lines.extend(["", "MACRO WATCH"])
    if macro_records:
        for record in macro_records:
            lines.append(
                (
                    f"{record['time_london']} — {record['event']} — "
                    f"{record['region']} — {record['importance']}"
                )
            )
    else:
        lines.append("No major macro events in the v1 manual calendar.")

    lines.extend(
        [
            "High-importance events may affect index futures, rates, FX, and sector leadership.",
            "",
            "NEXT WATCH POINTS",
            *next_watch_points(repeated_headlines, ticker_records, macro_records),
        ]
    )

    lines.extend(
        [
            "",
            "Generated automatically. Not a trade recommendation.",
        ]
    )
    return "\n".join(lines) + "\n"


def output_path_for_run_type(run_type: str) -> Path:
    return OUTPUT_DIR / f"{run_type}_briefing.md"


def archive_path_for_run_type(run_type: str, london_now: datetime) -> Path:
    date_part = london_now.strftime("%Y-%m-%d")
    time_part = london_now.strftime("%Y-%m-%d_%H%M")
    return OUTPUT_DIR / "archive" / date_part / f"{run_type}_briefing_{time_part}.md"


def write_text(output_path: Path, text: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def build_validation_summary(
    output_path: Path,
    archive_path: Path,
    repeated_headlines: list[dict[str, str]],
    ticker_records: list[dict[str, str]],
    macro_records: list[dict[str, str]],
    briefing_text: str,
) -> dict[str, Any]:
    return {
        "output_path": str(output_path),
        "archive_path": str(archive_path),
        "top_headlines_included": len(repeated_headlines),
        "key_tickers_included": len(ticker_records),
        "macro_events_included": len(macro_records),
        "line_count": len(briefing_text.splitlines()),
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Briefing writer validation summary:",
            f"Output path: {summary['output_path']}",
            f"Archive path: {summary['archive_path']}",
            f"Top headlines included: {summary['top_headlines_included']}",
            f"Key tickers included: {summary['key_tickers_included']}",
            f"Macro events included: {summary['macro_events_included']}",
            f"Approximate line count: {summary['line_count']}",
        ]
    )


def write_briefing(run_type: str) -> tuple[Path, dict[str, Any]]:
    repeated_headline_records = top_headlines(
        read_csv_records(REPEATED_HEADLINES_PATH)
    )
    ticker_records = key_tickers(read_csv_records(TICKER_FREQUENCY_PATH))
    macro_records = macro_events(read_csv_records(MACRO_CALENDAR_PATH))
    london_now = datetime.now(LONDON_TZ)
    briefing_text = render_briefing(
        run_type=run_type,
        repeated_headlines=repeated_headline_records,
        ticker_records=ticker_records,
        macro_records=macro_records,
        london_now=london_now,
    )
    output_path = write_text(output_path_for_run_type(run_type), briefing_text)
    archive_path = write_text(archive_path_for_run_type(run_type, london_now), briefing_text)
    summary = build_validation_summary(
        output_path=output_path,
        archive_path=archive_path,
        repeated_headlines=repeated_headline_records,
        ticker_records=ticker_records,
        macro_records=macro_records,
        briefing_text=briefing_text,
    )
    return output_path, summary
