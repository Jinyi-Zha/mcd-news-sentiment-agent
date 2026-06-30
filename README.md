# MCD News & Sentiment Agent

This project is a v1 foundation for a News & Sentiment Agent for equities briefings.

The final tool will produce short briefings for three daily run types:

- `eu_open`
- `us_open`
- `us_close`

The current stage includes the base structure and a Stage 1 Yahoo Finance headline pull. It does not analyse headlines or run automatically yet.

## How to Run

```bash
python main.py --run_type eu_open
python main.py --run_type us_open
python main.py --run_type us_close
python main.py --run_type eu_open --stage pull_yahoo
```

## Current Scope

- Project structure only
- `CLAUDE.md` project context
- Stage 1 Yahoo Finance ticker-level headline pull
- Raw Yahoo headline CSV saved to `data/raw/yahoo_headlines.csv`
- Minimal `main.py` that prints the selected run type and current London time
