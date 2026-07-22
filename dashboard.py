"""Streamlit dashboard for the MCD News & Sentiment Agent."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st


# The pipeline uses repository-relative paths. Keeping the dashboard anchored to
# this file makes it work consistently both locally and on Streamlit Cloud.
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

from main import RUN_ALL_STAGES, execute_stage  # noqa: E402


RUN_LABELS = {
    "eu_open": "EU Open",
    "us_open": "US Open",
    "us_close": "US Close",
}
BRIEFING_PATHS = {
    run_type: BASE_DIR / "outputs" / f"{run_type}_briefing.md"
    for run_type in RUN_LABELS
}
SECTION_HEADINGS = {
    "EXECUTIVE SUMMARY",
    "TOP MARKET THEMES",
    "KEY TICKERS TO WATCH",
    "MACRO WATCH",
    "NEXT WATCH POINTS",
}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def briefing_for_streamlit(raw_text: str) -> str:
    """Add Markdown headings while preserving the generated briefing text."""
    lines = raw_text.splitlines()
    if not lines:
        return ""

    rendered: list[str] = [f"## {lines[0]}"]
    for line in lines[1:]:
        if line.strip() in SECTION_HEADINGS:
            rendered.extend(["", f"### {line.strip()}", ""])
        else:
            rendered.append(line)
    return "\n".join(rendered)


def extract_briefing_metrics(raw_text: str) -> tuple[str, str, str]:
    timestamp_match = re.search(
        r"\|\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+[A-Z]{3,4})",
        raw_text,
    )
    theme_match = re.search(r"Evidence:\s*(\d+) sources / (\d+) headlines", raw_text)
    ticker_section = raw_text.partition("KEY TICKERS TO WATCH")[2].partition("MACRO WATCH")[0]
    ticker_count = len(re.findall(r"^\d+\.\s+[A-Z]{1,5}\s+—", ticker_section, re.MULTILINE))

    updated = timestamp_match.group(1) if timestamp_match else "Unavailable"
    top_evidence = (
        f"{theme_match.group(1)} sources / {theme_match.group(2)} headlines"
        if theme_match
        else "Unavailable"
    )
    return updated, top_evidence, str(ticker_count)


def run_selected_pipeline(run_type: str) -> None:
    progress = st.progress(0, text="Preparing pipeline...")
    messages: list[str] = []

    for index, stage in enumerate(RUN_ALL_STAGES, start=1):
        progress.progress(
            index / len(RUN_ALL_STAGES),
            text=f"Running {stage.replace('_', ' ')} ({index}/{len(RUN_ALL_STAGES)})",
        )
        result = execute_stage(stage=stage, run_type=run_type)
        messages.append(f"{stage}: {result['message']}")
        if stage == "validate_briefing" and result["summary"]["overall_status"] == "Failed":
            raise RuntimeError("The generated briefing failed its quality validation.")

    progress.empty()
    st.session_state["run_messages"] = messages
    st.session_state["run_success"] = (
        f"{RUN_LABELS[run_type]} briefing refreshed successfully at "
        f"{datetime.now(ZoneInfo('Europe/London')):%H:%M %Z}."
    )


st.set_page_config(
    page_title="MCD Market Intelligence",
    page_icon="📈",
    layout="wide",
)

st.title("MCD Market Intelligence")
st.caption(
    "Automated equities news monitoring for the EU open, US open and US close. "
    "Generated from Yahoo Finance and CNBC RSS."
)

with st.sidebar:
    st.header("Briefing controls")
    selected_run_type = st.selectbox(
        "Session",
        options=list(RUN_LABELS),
        format_func=RUN_LABELS.get,
    )
    refresh_clicked = st.button(
        "Refresh selected briefing",
        type="primary",
        use_container_width=True,
    )
    st.caption("A refresh fetches current public headlines and rebuilds the selected briefing.")
    st.divider()
    st.markdown(
        "**Data sources**  \n"
        "Yahoo Finance ticker news  \n"
        "CNBC public RSS feeds"
    )
    st.markdown(
        "**Coverage**  \n"
        "AAPL · MSFT · NVDA · AMZN · GOOGL · META · TSLA"
    )

if refresh_clicked:
    try:
        run_selected_pipeline(selected_run_type)
    except Exception as error:  # The page should remain usable if a source is unavailable.
        st.error("The refresh could not be completed. The latest saved briefing remains available.")
        with st.expander("Technical details"):
            st.exception(error)

if st.session_state.get("run_success"):
    st.success(st.session_state.pop("run_success"))
    messages = st.session_state.pop("run_messages", [])
    if messages:
        with st.expander("Refresh log"):
            for message in messages:
                st.write(message)

briefing_path = BRIEFING_PATHS[selected_run_type]
briefing_text = read_text(briefing_path)

if not briefing_text:
    st.warning(
        "No saved briefing is available for this session yet. "
        "Use ‘Refresh selected briefing’ to generate one."
    )
else:
    updated, top_evidence, ticker_count = extract_briefing_metrics(briefing_text)
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Last generated", updated)
    metric_2.metric("Top-theme evidence", top_evidence)
    metric_3.metric("Key tickers", ticker_count)

    briefing_tab, operations_tab, guide_tab = st.tabs(
        ["Market briefing", "Run status", "How to use"]
    )

    with briefing_tab:
        st.markdown(briefing_for_streamlit(briefing_text))
        st.download_button(
            "Download briefing",
            data=briefing_text,
            file_name=briefing_path.name,
            mime="text/markdown",
        )

    with operations_tab:
        run_summary = read_text(BASE_DIR / "outputs" / "run_summary.md")
        if run_summary:
            st.markdown(run_summary)
        else:
            st.info("No run summary is currently available.")

    with guide_tab:
        st.markdown(
            """
            1. Select **EU Open**, **US Open**, or **US Close** in the sidebar.
            2. Review the saved briefing and its generation time.
            3. Select **Refresh selected briefing** when an on-demand update is needed.
            4. Use **Download briefing** to save the Markdown output.

            The dashboard surfaces repeated market themes, key tickers, macro watch items,
            and next-session watch points. It is an informational monitoring tool and does
            not provide investment advice.
            """
        )

st.divider()
st.caption(
    "Generated automatically from public sources. Not a trade recommendation. "
    f"Dashboard time: {datetime.now(ZoneInfo('Europe/London')):%Y-%m-%d %H:%M %Z}."
)
