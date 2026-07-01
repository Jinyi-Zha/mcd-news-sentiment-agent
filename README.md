# MCD News & Sentiment Agent

## Project Goal

A lightweight equities briefing tool for a trading audience. It generates short, scannable market briefings for EU open, US open, and US close.

## V1 Scope

- Equities only
- Free data sources only
- Yahoo Finance ticker-level headlines
- CNBC RSS general headlines
- Rule-based filtering
- Rule-based repeated headline grouping
- Rule-based ticker frequency
- Manual v1 macro calendar
- Markdown briefing output
- Email delivery dry-run stub
- Not a research report
- Not a trade recommendation

## Pipeline

1. `pull_yahoo` - pulls ticker-level Yahoo Finance headlines for the default watchlist.
2. `pull_cnbc` - pulls general market headlines from free CNBC RSS feeds.
3. `combine_raw` - combines Yahoo and CNBC raw headline CSVs into one raw processed file.
4. `filter_equities` - applies a simple rule-based equities relevance filter.
5. `filter_recent` - keeps only headlines inside the run type lookback window.
6. `ticker_frequency` - counts key ticker and theme mentions.
7. `headline_repetition` - groups repeated or theme-similar headlines.
8. `macro_calendar` - writes today's manually maintained v1 macro calendar.
9. `write_briefing` - generates the final Markdown briefing.
10. `email_dry_run` - formats a future delivery email preview without sending it.

## How to Run

Set up the local environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the pipeline stages:

```bash
.venv/bin/python main.py --run_type eu_open --stage pull_yahoo
.venv/bin/python main.py --run_type eu_open --stage pull_cnbc
.venv/bin/python main.py --run_type eu_open --stage combine_raw
.venv/bin/python main.py --run_type eu_open --stage filter_equities
.venv/bin/python main.py --run_type eu_open --stage filter_recent
.venv/bin/python main.py --run_type eu_open --stage ticker_frequency
.venv/bin/python main.py --run_type eu_open --stage headline_repetition
.venv/bin/python main.py --run_type eu_open --stage macro_calendar
.venv/bin/python main.py --run_type eu_open --stage write_briefing
.venv/bin/python main.py --run_type eu_open --stage email_dry_run
```

Email delivery is currently dry-run only. The `email_dry_run` stage reads the generated Markdown briefing, formats a subject and body preview, and prints a placeholder recipient list. It does not use SMTP, API keys, secrets, or real sending.

## Run Types

- `eu_open` - EU market open briefing.
- `us_open` - US market open briefing.
- `us_close` - US market close briefing.

Default lookback windows:

- `eu_open`: 12 hours
- `us_open`: 8 hours
- `us_close`: 8 hours

For sample outputs, a 24-hour lookback can be used if local data is stale:

```bash
.venv/bin/python main.py --run_type us_open --stage filter_recent --lookback_hours 24
```

## Sample Outputs

- `outputs/eu_open_briefing.md`
- `outputs/us_open_briefing.md`
- `outputs/us_close_briefing.md`

## Output Format

```text
TOP HEADLINES
1. [story] - [source count] sources / [headline count] headlines - [tickers]

KEY TICKERS
1. [ticker] - inferred [count] / Yahoo feed [count] - [theme]

MACRO CALENDAR
[time] - [event] - [region] - [importance]

Generated automatically. Not a trade recommendation.
```

## Current Limitations

- Macro calendar is manual v1
- No live scheduler yet
- Email delivery is dry-run only; no real sending yet
- No LLM classification
- No dashboard
- No paid data sources
- Rule-based grouping may overlap themes
- Sample outputs depend on locally available headline data

## Suggested Future Improvements

- Automated scheduler
- More robust economic calendar source
- Better duplicate and near-duplicate detection
- Optional LLM-assisted classification after rule-based v1 is stable
- Production email or Slack distribution
- Dashboard only after core pipeline is reliable

## Final Delivery Notes

The project prioritises stability, readability, explainability, and avoiding over-building.
