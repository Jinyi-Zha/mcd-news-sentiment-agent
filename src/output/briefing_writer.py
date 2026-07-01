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
        "TOP HEADLINES",
    ]

    for index, record in enumerate(repeated_headlines, start=1):
        lines.extend(
            [
                (
                    f"{index}. {record['story_label']} — "
                    f"{record['source_count']} sources / "
                    f"{record['headline_count']} headlines — "
                    f"{record['related_tickers'] or 'N/A'}"
                ),
                f"   Rep: {record['representative_headline']}",
                "",
            ]
        )

    lines.append("KEY TICKERS")
    for index, record in enumerate(ticker_records, start=1):
        lines.append(
            (
                f"{index}. {record['ticker']} — inferred "
                f"{record['inferred_count']} / Yahoo feed "
                f"{record['yahoo_feed_count']} — {record['company_or_theme']}"
            )
        )

    lines.extend(["", "MACRO CALENDAR"])
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
