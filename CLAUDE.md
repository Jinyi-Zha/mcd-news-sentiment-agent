# MCD News & Sentiment Agent

## Project Goal

Build a News & Sentiment Agent for equities briefing. The agent should help produce short, scannable market briefings for an equities trading audience.

## Core Constraints

- Equities only.
- Free data sources only.
- V1 only uses Yahoo Finance and CNBC RSS.
- This is not a research report.
- This is not a trade recommendation.
- Each briefing should be readable in under 60 seconds.

## Daily Run Types

The agent is intended to run three times per day:

1. EU open
2. US open
3. US close

## Required Briefing Outputs

Each briefing must include three sections:

1. Most repeated headlines
2. Key tickers
3. Macro calendar

## V1 Scope

Keep v1 simple and reliable. Prioritise clean structure, readable output, and a pipeline that can be explained clearly. Do not overbuild sentiment scoring, dashboards, paid data integrations, full-market coverage, or automated scheduling until the manual v1 works.

## Output Style

The final briefing should be concise, structured, and useful for a trader to scan quickly. It should surface what the market is talking about, which equities are in focus, and what macro events are scheduled for the day.

