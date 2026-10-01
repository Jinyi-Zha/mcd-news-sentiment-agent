# MCD News & Sentiment Agent — Run Summary

Project name: MCD News & Sentiment Agent
Run type: us_close
Run time: 2026-10-02 00:49 BST
Overall status: Warning

## Pipeline Stages
- pull_yahoo
- pull_cnbc
- combine_raw
- filter_equities
- filter_recent
- ticker_frequency
- headline_repetition
- macro_calendar
- write_briefing
- email_dry_run

## Pipeline Outputs
- Briefing: outputs/us_close_briefing.md
- Archive briefing: outputs/archive/2026-10-02/us_close_briefing_2026-10-02_0049.md
- Email preview: outputs/email_preview/us_close_email.md
- Run summary: outputs/run_summary.md
- Archive run summary: outputs/archive/2026-10-02/run_summary_us_close_2026-10-02_0049.md

## Data Summary
- Top headlines included: 0
- Key tickers included: 1
- Macro events included: 0
- Approximate briefing line count: 21

## Quality Checks
- Briefing file exists: OK
- Briefing is not empty: OK
- Executive summary section exists: OK
- Top market themes section exists: OK
- Key tickers section exists: OK
- Macro watch section exists: OK
- Next watch points section exists: OK
- At least 3 market themes: WARNING
- At least 3 key tickers: WARNING
- At least 1 macro event: OK
- Email preview exists: OK
- Run summary exists: OK

## Warnings
- WARNING: fewer than 3 market themes found
- WARNING: fewer than 3 key tickers found

## Notes
Generated automatically. Not a trade recommendation.
