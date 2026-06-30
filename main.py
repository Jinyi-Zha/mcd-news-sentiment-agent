import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

from src.fetchers.yahoo_finance import (
    format_validation_summary,
    pull_and_save_yahoo_headlines,
)


VALID_RUN_TYPES = ("eu_open", "us_open", "us_close")
VALID_STAGES = ("pull_yahoo",)


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
        print(format_validation_summary(summary))


if __name__ == "__main__":
    main()
