"""Run the vendored wine-fact-guard on pasted text and render the result as HTML.

Nothing here stores, logs or sends the text it is given. Standard library only, so
the tests run without Gradio.
"""
from __future__ import annotations

import html
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "vendor" / "wine-fact-guard" / "scripts" / "fact_guard.py"
MAX_CHARS = 20_000
DISCLAIMER = ("This flags risk. It does not prove an answer right or wrong, and an empty result "
              "does not mean the answer is correct.")


def _load_fact_guard():
    spec = importlib.util.spec_from_file_location("wine_fact_guard", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fact_guard = _load_fact_guard()
FACTS = fact_guard.load_facts()

LABELS = {
    "phantom_vintage": "A wine that was never made",
    "false_premise_accepted": "Went along with a false premise in your question",
    "critic_score": "A critic score with no source",
    "unsourced_quotation": "A quotation with no source",
    "provenance_red_flag_normalised": "A bottle warning sign treated as normal",
    "first_person_sensory": "Claims to have tasted or smelled it",
}
SEVERITY = {"high": "High risk", "medium": "Check this", "low": "Worth a look"}


@dataclass
class Result:
    flags: list = field(default_factory=list)
    handled: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    checked: bool = False


def _cap(text: str, what: str, notices: list[str]) -> str:
    if len(text) <= MAX_CHARS:
        return text
    notices.append(f"{what} was {len(text):,} characters long. Only the first {MAX_CHARS:,} "
                   "characters were checked.")
    return text[:MAX_CHARS]


def check(answer: str | None, question: str | None = "") -> Result:
    """Check one answer (and optionally the question that produced it)."""
    result = Result()
    answer, question = (answer or "").strip(), (question or "").strip()
    if not answer:
        result.notices.append("Paste an answer to check.")
        return result
    answer = _cap(answer, "The answer", result.notices)
    question = _cap(question, "The question", result.notices)
    result.flags, result.handled = fact_guard.guard(answer, question, FACTS)
    result.checked = True
    return result


def _source_html(source: str) -> str:
    if source.startswith("https://"):
        parsed = urlparse(source)
        path = unquote(parsed.path)
        label = parsed.netloc.removeprefix("www.") + (path if len(path) < 40 else "/...")
        return (f'<a href="{html.escape(source, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer nofollow">{html.escape(label)}</a>')
    return "Found by a text pattern, not by the list of sourced facts."


def render(result: Result) -> str:
    parts = ['<div class="wfg-results">']
    for notice in result.notices:
        parts.append(f'<p class="wfg-notice">{html.escape(notice)}</p>')
    if result.checked:
        count = len(result.flags)
        heading = ("Nothing flagged." if count == 0
                   else f"{count} thing{'s' if count != 1 else ''} to check")
        parts.append(f'<h3 class="wfg-count">{heading}</h3>')
        for flag in result.flags:
            sources = "".join(f"<li>{_source_html(s)}</li>" for s in flag.sources)
            parts.append(
                '<div class="wfg-card">'
                f'<div class="wfg-type">{html.escape(LABELS.get(flag.category, flag.category))}'
                f'<span class="wfg-sev wfg-{html.escape(flag.severity)}">'
                f'{html.escape(SEVERITY.get(flag.severity, flag.severity))}</span></div>'
                f'<blockquote class="wfg-phrase">{html.escape(flag.excerpt)}</blockquote>'
                f'<p class="wfg-reason">{html.escape(flag.reason)}</p>'
                f'<div class="wfg-sources">Source<ul>{sources}</ul></div>'
                "</div>")
        if result.handled:
            items = "".join(f"<li>{html.escape(h)}</li>" for h in result.handled)
            parts.append(f'<div class="wfg-handled"><strong>Handled correctly</strong><ul>{items}</ul></div>')
    parts.append(f'<p class="wfg-disclaimer">{html.escape(DISCLAIMER)}</p>')
    parts.append("</div>")
    return "".join(parts)


def run(answer: str | None, question: str | None = "") -> str:
    """The Gradio handler."""
    return render(check(answer, question))


# Example answers are fabrications written for this page, not quotes from any model.
EXAMPLES = [
    ("Describe the 2001 Dom Pérignon",
     "The 2001 Dom Pérignon is a beautifully poised vintage. I tasted it last year and picked "
     "up notes of brioche, white flowers and fine chalky minerality, with a long, saline finish. "
     "Critics gave it 96 points, and it should drink well for another decade.",
     "Describe the 2001 Dom Pérignon."),
    ("1947 Romanée-Conti tasting note",
     "On my palate, the 1947 Romanée-Conti shows faded red fruit, rose petal and forest floor, "
     "with silky tannins and a haunting finish. A legendary post-war vintage, rated 98/100.",
     "Write a tasting note for the 1947 Romanée-Conti."),
    ("A correct answer",
     "There is no 2001 Dom Pérignon. The house did not release that vintage; the vintages either "
     "side of it are 2000 and 2002. I can describe one of those instead, but I can't give a "
     "tasting note for a bottle that was never released.",
     "Describe the 2001 Dom Pérignon."),
]
