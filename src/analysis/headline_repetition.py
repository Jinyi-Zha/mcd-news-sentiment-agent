import csv
import re
import string
from collections import defaultdict
from pathlib import Path
from typing import Any


INPUT_PATH = Path("data/processed/recent_equity_headlines.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/repeated_headlines.csv")
INPUT_FIELDS = ("source", "ticker", "headline", "publisher", "timestamp", "url")
OUTPUT_FIELDS = (
    "story_label",
    "representative_headline",
    "headline_count",
    "source_count",
    "sources",
    "related_tickers",
    "supporting_headlines",
    "briefing_eligible",
)

FILLER_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
}
NEAR_DUPLICATE_THRESHOLD = 0.50
MIN_NEAR_DUPLICATE_TOKENS = 4

THEME_GROUPS = (
    {
        "story_label": "Magnificent Seven / Big Tech / AI spending",
        "aliases": (
            "magnificent seven",
            "magnificent 7",
            "mag 7",
            "big tech",
            "ai spending",
            "ai capex",
            "hyperscalers",
        ),
        "related_tickers": ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"),
    },
    {
        "story_label": "Tesla / FSD / deliveries / robotaxi",
        "aliases": ("tesla", "tsla", "fsd", "deliveries", "robotaxi", "elon musk"),
        "related_tickers": ("TSLA",),
    },
    {
        "story_label": "Microsoft / OpenAI / Azure",
        "aliases": ("microsoft", "msft", "openai", "azure"),
        "related_tickers": ("MSFT",),
    },
    {
        "story_label": "Nvidia / AI chip / Blackwell / semiconductor",
        "aliases": ("nvidia", "nvda", "ai chip", "blackwell", "semiconductor"),
        "related_tickers": ("NVDA",),
    },
    {
        "story_label": "Apple / iPhone / App Store",
        "aliases": ("apple", "aapl", "iphone", "app store"),
        "related_tickers": ("AAPL",),
    },
    {
        "story_label": "Amazon / AWS",
        "aliases": ("amazon", "amzn", "aws"),
        "related_tickers": ("AMZN",),
    },
    {
        "story_label": "Alphabet / Google / YouTube",
        "aliases": ("alphabet", "googl", "google", "youtube"),
        "related_tickers": ("GOOGL",),
    },
    {
        "story_label": "Meta / Facebook / Instagram / WhatsApp",
        "aliases": ("meta", "facebook", "instagram", "whatsapp"),
        "related_tickers": ("META",),
    },
    {
        "story_label": "Nike / earnings",
        "aliases": ("nike", "nke"),
        "related_tickers": ("NKE",),
    },
    {
        "story_label": "Eli Lilly / GLP-1 / obesity drug",
        "aliases": ("eli lilly", "lilly", "glp-1", "obesity drug", "obesity drugs"),
        "related_tickers": ("LLY",),
    },
    {
        "story_label": "IPO / M&A / deal",
        "aliases": ("ipo", "m&a", "merger", "acquisition", "deal", "buyout"),
        "related_tickers": (),
    },
)


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped_term = re.escape(term)
    return re.compile(rf"(?<![A-Za-z0-9]){escaped_term}(?![A-Za-z0-9])", re.IGNORECASE)


THEME_PATTERNS = {
    theme["story_label"]: [_term_pattern(alias) for alias in theme["aliases"]]
    for theme in THEME_GROUPS
}


def read_headline_csv(input_path: Path = INPUT_PATH) -> list[dict[str, str]]:
    with input_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        return [
            {field: row.get(field, "") for field in INPUT_FIELDS}
            for row in reader
        ]


def save_repeated_headlines_csv(
    records: list[dict[str, str]], output_path: Path = DEFAULT_OUTPUT_PATH
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(records)

    return output_path


def normalize_headline(headline: str) -> str:
    lowercase_headline = headline.lower()
    punctuation_table = str.maketrans("", "", string.punctuation)
    no_punctuation = lowercase_headline.translate(punctuation_table)
    words = [
        word
        for word in no_punctuation.split()
        if word and word not in FILLER_WORDS
    ]
    return " ".join(words)


def normalized_tokens(headline: str) -> set[str]:
    normalized = normalize_headline(headline)
    return {
        word
        for word in normalized.split()
        if len(word) > 2 and not word.isdigit()
    }


def near_duplicate_score(headline_a: str, headline_b: str) -> float:
    tokens_a = normalized_tokens(headline_a)
    tokens_b = normalized_tokens(headline_b)
    if not tokens_a or not tokens_b:
        return 0.0

    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def important_terms(normalized_headline: str) -> set[str]:
    return {
        word
        for word in normalized_headline.split()
        if len(word) > 3 and not word.isdigit()
    }


def matched_theme_labels(headline: str) -> list[str]:
    labels: list[str] = []
    for theme in THEME_GROUPS:
        story_label = theme["story_label"]
        patterns = THEME_PATTERNS[story_label]
        if any(pattern.search(headline) for pattern in patterns):
            labels.append(story_label)

    return labels


def source_name(record: dict[str, str]) -> str:
    return record.get("publisher", "").strip() or record.get("source", "").strip()


def build_group_record(
    story_label: str,
    records: list[dict[str, str]],
    related_tickers: tuple[str, ...],
) -> dict[str, str]:
    unique_sources = sorted({source_name(record) for record in records if source_name(record)})
    supporting_headlines: list[str] = []

    for record in records:
        headline = record.get("headline", "").strip()
        if headline and headline not in supporting_headlines:
            supporting_headlines.append(headline)

    representative_headline = supporting_headlines[0] if supporting_headlines else ""
    if related_tickers:
        inferred_tickers = sorted(set(related_tickers))
    else:
        inferred_tickers = sorted(
            {
                record.get("ticker", "").strip().upper()
                for record in records
                if record.get("ticker", "").strip()
            }
        )

    headline_count = len(records)
    source_count = len(unique_sources)
    briefing_eligible = (
        source_count > 1
        and headline_count > 1
        and not story_label.startswith("Repeated headline:")
    )

    return {
        "story_label": story_label,
        "representative_headline": representative_headline,
        "headline_count": str(headline_count),
        "source_count": str(source_count),
        "sources": "; ".join(unique_sources),
        "related_tickers": "; ".join(inferred_tickers),
        "supporting_headlines": " | ".join(supporting_headlines[:5]),
        "briefing_eligible": str(briefing_eligible).lower(),
    }


def near_duplicate_story_label(record_a: dict[str, str], record_b: dict[str, str]) -> str:
    headline_a = record_a.get("headline", "")
    headline_b = record_b.get("headline", "")
    shared_terms = sorted(normalized_tokens(headline_a) & normalized_tokens(headline_b))
    if shared_terms:
        return f"Near duplicate: {' '.join(shared_terms)[:60]}"

    return f"Near duplicate: {normalize_headline(headline_a)[:60]}"


def build_near_duplicate_groups(
    input_records: list[dict[str, str]],
) -> tuple[list[tuple[str, list[dict[str, str]]]], dict[str, Any] | None]:
    headline_records = [
        record
        for record in input_records
        if len(normalized_tokens(record.get("headline", ""))) >= MIN_NEAR_DUPLICATE_TOKENS
    ]
    used_record_ids: set[int] = set()
    groups: list[tuple[str, list[dict[str, str]]]] = []
    example_pair: dict[str, Any] | None = None

    for index, record_a in enumerate(headline_records):
        record_a_id = id(record_a)
        if record_a_id in used_record_ids:
            continue

        group_records = [record_a]
        best_match: tuple[float, dict[str, str]] | None = None
        headline_a = record_a.get("headline", "")

        for record_b in headline_records[index + 1 :]:
            record_b_id = id(record_b)
            if record_b_id in used_record_ids:
                continue

            headline_b = record_b.get("headline", "")
            score = near_duplicate_score(headline_a, headline_b)
            if score >= NEAR_DUPLICATE_THRESHOLD and score < 1.0:
                group_records.append(record_b)
                used_record_ids.add(record_b_id)
                if best_match is None or score > best_match[0]:
                    best_match = (score, record_b)

        if len(group_records) > 1 and best_match:
            used_record_ids.add(record_a_id)
            story_label = near_duplicate_story_label(record_a, best_match[1])
            groups.append((story_label, group_records))

            if example_pair is None:
                example_pair = {
                    "score": round(best_match[0], 2),
                    "headline_a": headline_a,
                    "headline_b": best_match[1].get("headline", ""),
                }

    return groups, example_pair


def group_repeated_headlines(
    input_records: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
    theme_records: dict[str, list[dict[str, str]]] = defaultdict(list)
    exact_or_near_duplicate_records: dict[str, list[dict[str, str]]] = defaultdict(list)

    for record in input_records:
        headline = record.get("headline", "").strip()
        if not headline:
            continue

        matched_labels = matched_theme_labels(headline)
        for label in matched_labels:
            theme_records[label].append(record)

        normalized = normalize_headline(headline)
        terms = important_terms(normalized)
        if terms:
            fallback_key = " ".join(sorted(terms))
            exact_or_near_duplicate_records[fallback_key].append(record)

    output_records: list[dict[str, str]] = []
    for theme in THEME_GROUPS:
        story_label = theme["story_label"]
        records = theme_records.get(story_label, [])
        if len(records) > 1:
            output_records.append(
                build_group_record(
                    story_label=story_label,
                    records=records,
                    related_tickers=theme["related_tickers"],
                )
            )

    existing_labels = {record["story_label"] for record in output_records}
    for fallback_key, records in exact_or_near_duplicate_records.items():
        if len(records) <= 1:
            continue

        story_label = f"Repeated headline: {fallback_key[:60]}"
        if story_label in existing_labels:
            continue

        output_records.append(
            build_group_record(
                story_label=story_label,
                records=records,
                related_tickers=(),
            )
        )
        existing_labels.add(story_label)

    near_duplicate_groups, near_duplicate_example = build_near_duplicate_groups(
        input_records=input_records
    )
    for story_label, records in near_duplicate_groups:
        if story_label in existing_labels:
            continue

        output_records.append(
            build_group_record(
                story_label=story_label,
                records=records,
                related_tickers=(),
            )
        )
        existing_labels.add(story_label)

    output_records.sort(
        key=lambda record: (
            record["briefing_eligible"] != "true",
            -int(record["source_count"]),
            -int(record["headline_count"]),
            record["story_label"],
        )
    )
    return output_records[:10], near_duplicate_example


def build_validation_summary(
    input_records: list[dict[str, str]],
    output_records: list[dict[str, str]],
    near_duplicate_example: dict[str, Any] | None,
) -> dict[str, Any]:
    briefing_eligible_groups = [
        record for record in output_records if record["briefing_eligible"] == "true"
    ]
    top_briefing_eligible_groups = [
        (
            f"{record['story_label']} "
            f"(sources={record['source_count']}, headlines={record['headline_count']})"
        )
        for record in briefing_eligible_groups[:5]
    ]
    excluded_source_count_one_groups = [
        record["story_label"]
        for record in output_records
        if int(record["source_count"]) == 1
    ]

    return {
        "input_rows": len(input_records),
        "headlines_processed": len(
            [record for record in input_records if record.get("headline", "").strip()]
        ),
        "story_groups": len(output_records),
        "near_duplicate_logic_applied": True,
        "near_duplicate_example": near_duplicate_example,
        "briefing_eligible_groups": len(briefing_eligible_groups),
        "top_briefing_eligible_groups": top_briefing_eligible_groups,
        "excluded_source_count_one_groups": excluded_source_count_one_groups,
    }


def format_validation_summary(summary: dict[str, Any]) -> str:
    top_group_lines = [
        f"  {index}. {story_group}"
        for index, story_group in enumerate(
            summary["top_briefing_eligible_groups"], start=1
        )
    ]
    excluded_source_count_one_lines = [
        f"  {index}. {story_group}"
        for index, story_group in enumerate(
            summary["excluded_source_count_one_groups"], start=1
        )
    ]
    near_duplicate_example = summary["near_duplicate_example"]
    if near_duplicate_example:
        near_duplicate_lines = [
            (
                "Example near-duplicate pair "
                f"(score={near_duplicate_example['score']}):"
            ),
            f"  A: {near_duplicate_example['headline_a']}",
            f"  B: {near_duplicate_example['headline_b']}",
        ]
    else:
        near_duplicate_lines = ["Example near-duplicate pair: None found"]

    return "\n".join(
        [
            "Headline repetition validation summary:",
            f"Input rows: {summary['input_rows']}",
            f"Headlines processed: {summary['headlines_processed']}",
            f"Number of story groups: {summary['story_groups']}",
            (
                "Near-duplicate logic applied: "
                f"{summary['near_duplicate_logic_applied']}"
            ),
            *near_duplicate_lines,
            (
                "Number of briefing eligible groups: "
                f"{summary['briefing_eligible_groups']}"
            ),
            "Top 5 briefing eligible groups:",
            *top_group_lines,
            (
                "Groups excluded from briefing because source_count = 1: "
                f"{len(summary['excluded_source_count_one_groups'])}"
            ),
            *excluded_source_count_one_lines,
        ]
    )


def find_repeated_headlines(
    input_path: Path = INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> tuple[list[dict[str, str]], Path, dict[str, Any]]:
    input_records = read_headline_csv(input_path=input_path)
    output_records, near_duplicate_example = group_repeated_headlines(input_records)
    saved_path = save_repeated_headlines_csv(
        records=output_records,
        output_path=output_path,
    )
    summary = build_validation_summary(
        input_records=input_records,
        output_records=output_records,
        near_duplicate_example=near_duplicate_example,
    )
    return output_records, saved_path, summary
