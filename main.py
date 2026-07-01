import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from src.analysis.ticker_frequency import (
    count_ticker_frequency,
    format_validation_summary as format_ticker_frequency_validation_summary,
)
from src.analysis.headline_repetition import (
    find_repeated_headlines,
    format_validation_summary as format_headline_repetition_validation_summary,
)
from src.analysis.macro_calendar import (
    build_macro_calendar,
    format_validation_summary as format_macro_calendar_validation_summary,
)
from src.fetchers.cnbc_rss import (
    format_validation_summary as format_cnbc_validation_summary,
)
from src.fetchers.cnbc_rss import pull_and_save_cnbc_headlines
from src.fetchers.yahoo_finance import (
    format_validation_summary as format_yahoo_validation_summary,
    pull_and_save_yahoo_headlines,
)
from src.processing.combine_raw import (
    combine_raw_headlines,
    format_validation_summary as format_combined_raw_validation_summary,
)
from src.processing.equity_filter import (
    filter_equity_headlines,
    format_validation_summary as format_equity_filter_validation_summary,
)
from src.processing.time_filter import (
    filter_recent_headlines,
    format_validation_summary as format_recent_validation_summary,
)


VALID_RUN_TYPES = ("eu_open", "us_open", "us_close")
VALID_STAGES = (
    "pull_yahoo",
    "pull_cnbc",
    "combine_raw",
    "filter_equities",
    "filter_recent",
    "ticker_frequency",
    "headline_repetition",
    "macro_calendar",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MCD equities briefing agent entry point."
    )
    parser.add_argument(
        "--run_type",
        required=True,
        choices=VALID_RUN_TYPES,
        help="Briefing run type to execute.",
    )
    parser.add_argument(
        "--stage",
        choices=VALID_STAGES,
        help="Optional Stage 1 task to run.",
    )
    parser.add_argument(
        "--lookback_hours",
        type=float,
        help="Optional lookback window in hours for filter_recent.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    london_now = datetime.now(ZoneInfo("Europe/London"))

    print("MCD News & Sentiment Agent")
    print(f"Run type: {args.run_type}")
    print(f"Current London time: {london_now:%Y-%m-%d %H:%M:%S %Z}")

    if args.stage == "pull_yahoo":
        records, saved_path, summary = pull_and_save_yahoo_headlines()
        print(f"Stage: {args.stage}")
        print(f"Yahoo headlines pulled: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_yahoo_validation_summary(summary))

    if args.stage == "pull_cnbc":
        records, saved_path, summary = pull_and_save_cnbc_headlines()
        print(f"Stage: {args.stage}")
        print(f"CNBC RSS headlines pulled: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_cnbc_validation_summary(summary))

    if args.stage == "combine_raw":
        records, saved_path, summary = combine_raw_headlines()
        print(f"Stage: {args.stage}")
        print(f"Combined raw headlines: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_combined_raw_validation_summary(summary))

    if args.stage == "filter_equities":
        records, saved_path, summary, _removed_records = filter_equity_headlines()
        print(f"Stage: {args.stage}")
        print(f"Filtered equity headlines: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_equity_filter_validation_summary(summary))

    if args.stage == "filter_recent":
        records, saved_path, summary = filter_recent_headlines(
            run_type=args.run_type,
            lookback_hours=args.lookback_hours,
        )
        print(f"Stage: {args.stage}")
        print(f"Recent equity headlines: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_recent_validation_summary(summary))

    if args.stage == "ticker_frequency":
        records, saved_path, summary = count_ticker_frequency()
        print(f"Stage: {args.stage}")
        print(f"Ticker frequency rows: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_ticker_frequency_validation_summary(summary))

    if args.stage == "headline_repetition":
        records, saved_path, summary = find_repeated_headlines()
        print(f"Stage: {args.stage}")
        print(f"Repeated headline groups: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        print(format_headline_repetition_validation_summary(summary))

    if args.stage == "macro_calendar":
        records, saved_path, summary = build_macro_calendar()
        print(f"Stage: {args.stage}")
        print(f"Macro calendar events: {len(records)}")
        print(f"Saved CSV: {saved_path}")
        if not records:
            print("No macro events found for today in the v1 manual calendar.")
        print(format_macro_calendar_validation_summary(summary))


if __name__ == "__main__":
    main()
