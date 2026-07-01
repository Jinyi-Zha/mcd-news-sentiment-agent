import argparse
from datetime import datetime
from typing import Any
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
from src.output.briefing_writer import (
    format_validation_summary as format_briefing_validation_summary,
)
from src.output.briefing_writer import write_briefing
from src.output.email_sender import (
    email_dry_run,
    format_dry_run_summary as format_email_dry_run_summary,
)
from src.output.run_summary import (
    create_run_summary,
    format_quality_validation_summary,
    format_validation_summary as format_run_summary_validation_summary,
    validate_briefing_quality,
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
    "write_briefing",
    "email_dry_run",
    "run_summary",
    "validate_briefing",
)
RUN_ALL_STAGES = (
    "pull_yahoo",
    "pull_cnbc",
    "combine_raw",
    "filter_equities",
    "filter_recent",
    "ticker_frequency",
    "headline_repetition",
    "macro_calendar",
    "write_briefing",
    "email_dry_run",
    "run_summary",
    "validate_briefing",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the MCD equities briefing agent entry point."
    )
    parser.add_argument(
        "--run_type",
        choices=VALID_RUN_TYPES,
        help="Briefing run type to execute.",
    )
    parser.add_argument(
        "--run_all",
        action="store_true",
        help="Run the full daily briefing pack for all run types.",
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
    args = parser.parse_args()
    if args.run_all and args.stage:
        parser.error("--run_all cannot be combined with --stage.")
    if args.run_all and args.run_type:
        parser.error("--run_all cannot be combined with --run_type.")
    if not args.run_all and not args.run_type:
        parser.error("--run_type is required unless --run_all is used.")
    return args


def execute_stage(
    stage: str,
    run_type: str,
    lookback_hours: float | None = None,
) -> dict[str, Any]:
    if stage == "pull_yahoo":
        records, saved_path, summary = pull_and_save_yahoo_headlines()
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Yahoo headlines pulled: {len(records)}",
            "validation": format_yahoo_validation_summary(summary),
        }

    if stage == "pull_cnbc":
        records, saved_path, summary = pull_and_save_cnbc_headlines()
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"CNBC RSS headlines pulled: {len(records)}",
            "validation": format_cnbc_validation_summary(summary),
        }

    if stage == "combine_raw":
        records, saved_path, summary = combine_raw_headlines()
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Combined raw headlines: {len(records)}",
            "validation": format_combined_raw_validation_summary(summary),
        }

    if stage == "filter_equities":
        records, saved_path, summary, _removed_records = filter_equity_headlines()
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Filtered equity headlines: {len(records)}",
            "validation": format_equity_filter_validation_summary(summary),
        }

    if stage == "filter_recent":
        records, saved_path, summary = filter_recent_headlines(
            run_type=run_type,
            lookback_hours=lookback_hours,
        )
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Recent equity headlines: {len(records)}",
            "validation": format_recent_validation_summary(summary),
        }

    if stage == "ticker_frequency":
        records, saved_path, summary = count_ticker_frequency()
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Ticker frequency rows: {len(records)}",
            "validation": format_ticker_frequency_validation_summary(summary),
        }

    if stage == "headline_repetition":
        records, saved_path, summary = find_repeated_headlines()
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Repeated headline groups: {len(records)}",
            "validation": format_headline_repetition_validation_summary(summary),
        }

    if stage == "macro_calendar":
        records, saved_path, summary = build_macro_calendar()
        no_events_message = ""
        if not records:
            no_events_message = "\nNo macro events found for today in the config-driven calendar."
        return {
            "summary": summary,
            "output_path": saved_path,
            "message": f"Macro calendar events: {len(records)}",
            "validation": format_macro_calendar_validation_summary(summary) + no_events_message,
        }

    if stage == "write_briefing":
        output_path, summary = write_briefing(run_type=run_type)
        _, run_summary = create_run_summary(
            run_type=run_type,
            briefing_summary=summary,
        )
        return {
            "summary": summary,
            "output_path": output_path,
            "message": f"Saved briefing: {output_path}",
            "validation": (
                format_briefing_validation_summary(summary)
                + "\n"
                + format_run_summary_validation_summary(run_summary)
            ),
        }

    if stage == "email_dry_run":
        email_payload = email_dry_run(run_type=run_type)
        _, run_summary = create_run_summary(
            run_type=run_type,
            email_payload=email_payload,
        )
        return {
            "summary": email_payload,
            "output_path": email_payload["preview_path"],
            "message": f"Saved email preview: {email_payload['preview_path']}",
            "validation": (
                format_email_dry_run_summary(email_payload)
                + "\n"
                + format_run_summary_validation_summary(run_summary)
            ),
        }

    if stage == "run_summary":
        output_path, summary = create_run_summary(run_type=run_type)
        return {
            "summary": summary,
            "output_path": output_path,
            "message": f"Run summary saved: {output_path}",
            "validation": format_run_summary_validation_summary(summary),
        }

    if stage == "validate_briefing":
        summary = validate_briefing_quality(run_type=run_type)
        return {
            "summary": summary,
            "output_path": summary["briefing_path"],
            "message": f"Briefing validation status: {summary['overall_status']}",
            "validation": format_quality_validation_summary(summary),
        }

    raise ValueError(f"Unsupported stage: {stage}")


def print_single_stage_result(stage: str, result: dict[str, Any]) -> None:
    print(f"Stage: {stage}")
    print(result["message"])
    if result.get("output_path"):
        print(f"Output path: {result['output_path']}")
    print(result["validation"])


def run_daily_pack() -> None:
    successful_run_types: list[str] = []
    failed_run_types: list[str] = []

    print("Running full daily briefing pack...")
    for index, run_type in enumerate(VALID_RUN_TYPES, start=1):
        print()
        print(f"[{index}/{len(VALID_RUN_TYPES)}] {run_type}")
        run_type_failed = False

        for stage in RUN_ALL_STAGES:
            try:
                result = execute_stage(stage=stage, run_type=run_type)
                if stage == "validate_briefing":
                    status = result["summary"]["overall_status"]
                    print(f"  {stage}: {status}")
                    if status == "Failed":
                        run_type_failed = True
                        break
                else:
                    print(f"  {stage}: OK")
            except Exception as error:  # noqa: BLE001 - run_all should keep operating.
                print(f"  {stage}: WARNING - {error}")
                run_type_failed = True
                break

        if run_type_failed:
            failed_run_types.append(run_type)
        else:
            successful_run_types.append(run_type)

    print()
    print("Daily briefing pack complete.")
    print()
    print("Generated:")
    generated_paths = [
        "outputs/eu_open_briefing.md",
        "outputs/us_open_briefing.md",
        "outputs/us_close_briefing.md",
        "outputs/email_preview/eu_open_email.md",
        "outputs/email_preview/us_open_email.md",
        "outputs/email_preview/us_close_email.md",
        "outputs/run_summary.md",
    ]
    for path in generated_paths:
        print(f"- {path}")

    print()
    print(f"Successful run types: {len(successful_run_types)}")
    print(f"Failed run types: {len(failed_run_types)}")
    if failed_run_types:
        print(f"Failed run types: {', '.join(failed_run_types)}")


def main() -> None:
    args = parse_args()
    london_now = datetime.now(ZoneInfo("Europe/London"))

    print("MCD News & Sentiment Agent")
    print(f"Current London time: {london_now:%Y-%m-%d %H:%M:%S %Z}")

    if args.run_all:
        run_daily_pack()
        return

    print(f"Run type: {args.run_type}")
    if not args.stage:
        return

    result = execute_stage(
        stage=args.stage,
        run_type=args.run_type,
        lookback_hours=args.lookback_hours,
    )
    print_single_stage_result(stage=args.stage, result=result)


if __name__ == "__main__":
    main()
