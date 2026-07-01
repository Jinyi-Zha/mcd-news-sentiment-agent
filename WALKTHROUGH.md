# MCD News & Sentiment Agent — Walkthrough

## 1. Project Goal

The MCD News & Sentiment Agent is a lightweight V1 equities briefing agent. It creates short, market-focused briefings for:

- EU open
- US open
- US close

The briefing is designed for a trading / markets audience that needs a quick view of repeated equity stories, key tickers in focus, and important macro events. It is not a research report and it is not a trade recommendation.

## 2. What the Agent Produces

Main latest-output files:

- `outputs/eu_open_briefing.md`
- `outputs/us_open_briefing.md`
- `outputs/us_close_briefing.md`
- `outputs/email_preview/eu_open_email.md`
- `outputs/email_preview/us_open_email.md`
- `outputs/email_preview/us_close_email.md`
- `outputs/run_summary.md`

Timestamped archive files are saved under:

- `outputs/archive/YYYY-MM-DD/`

The latest files are overwritten on each run and are useful for quick review. The archive files keep timestamped copies, which makes it easier to audit what was generated at a specific run time.

## 3. How to Run It Locally

Set up the local environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run individual review stages:

```bash
.venv/bin/python main.py --run_type eu_open --stage write_briefing
.venv/bin/python main.py --run_type eu_open --stage email_dry_run
.venv/bin/python main.py --run_type eu_open --stage run_summary
.venv/bin/python main.py --run_type eu_open --stage validate_briefing
```

Run the full daily briefing pack for all three run types:

```bash
.venv/bin/python main.py --run_all
```

## 4. Pipeline Overview

1. `pull_yahoo`
   Pulls ticker-level Yahoo Finance headlines for the default equity watchlist. It creates raw Yahoo headline data.

2. `pull_cnbc`
   Pulls general market headlines from free CNBC RSS feeds. It creates raw CNBC headline data.

3. `combine_raw`
   Combines the Yahoo and CNBC raw headline files into one combined raw headline file.

4. `filter_equities`
   Applies a rule-based equities relevance filter. It keeps headlines that appear relevant to stocks, sectors, companies, or equity indices.

5. `filter_recent`
   Applies the run-type lookback window so the briefing focuses on recent market discussion.

6. `ticker_frequency`
   Counts ticker and theme mentions using Yahoo feed tickers plus rule-based inferred mentions from general headlines.

7. `headline_repetition`
   Groups repeated, theme-similar, and lightweight near-duplicate headlines to identify the most repeated market stories.

8. `macro_calendar`
   Reads the manual/config-driven macro calendar and writes today's macro events into the processed data folder.

9. `write_briefing`
   Generates the final Markdown briefing and saves both the latest briefing file and a timestamped archive copy.

10. `email_dry_run`
    Creates a reviewable Markdown email preview. It does not send real emails.

11. `run_summary`
    Creates an operational run log showing generated files, data counts, quality checks, and warnings.

12. `validate_briefing`
    Runs the quality validation gate to check whether the briefing is complete enough for review.

## 5. Scheduled Cloud Automation

GitHub Actions is configured to run the workflow automatically for:

- EU open
- US open
- US close

GitHub Actions cron schedules use UTC. Because London switches between GMT and BST, the scheduled times should be reviewed when daylight saving changes. The workflow can also be run manually through the GitHub Actions tab.

No new workflow logic is added by this walkthrough.

## 6. Briefing Format

The current briefing is structured around:

- Executive Summary
- Top Market Themes
- Key Tickers to Watch
- Macro Watch
- Next Watch Points

This format is useful for a trader / market intelligence audience because it separates the main market themes, ticker-specific evidence, macro context, and what to monitor next. The goal is a short briefing that can be read quickly rather than a long research note.

## 7. Email Delivery Preview

`email_dry_run` does not send real emails. It creates reviewable Markdown email previews under `outputs/email_preview/`.

This is a safe handoff step before any future production connection to SMTP, Gmail, Outlook, Slack, or Teams. No credentials, API keys, or secrets are used in the current version.

## 8. Run Summary and Quality Validation

`run_summary` creates an operational run log at `outputs/run_summary.md` and a timestamped archive copy.

`validate_briefing` checks whether the briefing appears complete enough for a trader-facing market intelligence note. Status values are:

- `Success` - all core quality checks pass.
- `Warning` - the briefing exists, but one or more checks are weak or missing.
- `Failed` - the briefing file is missing or empty.

Example checks include:

- briefing file exists
- required sections exist
- at least 3 market themes
- at least 3 key tickers
- macro events exist
- email preview exists
- run summary exists

## 9. Current Limitations

- Free RSS/headline sources only
- Rule-based classification
- No LLM classification
- No paid market data
- No live execution or trading
- Email is dry-run only
- Macro calendar is config-driven/manual v2
- No dashboard yet
- Sample output depends on available local headline data

## 10. Suggested Future Improvements

- Connect compliant SMTP, Gmail, Outlook, Slack, or Teams delivery
- Improve source coverage
- Integrate a compliant economic calendar API
- Add richer duplicate detection or optional LLM-assisted classification
- Add a dashboard only after the pipeline is stable
- Add more robust monitoring and error alerts

## 11. Review Checklist

- README explains scope
- GitHub Actions workflow exists
- Sample briefings exist
- Email previews exist
- Macro calendar config exists
- Run summary exists
- Validation gate exists
- `run_all` command exists

## 12. Final Note

This project prioritises stability, explainability, and safe automation over over-engineering. It is a V1 market intelligence briefing agent suitable for review and further extension.
