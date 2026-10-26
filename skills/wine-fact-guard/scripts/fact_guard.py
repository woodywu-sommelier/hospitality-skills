#!/usr/bin/env python3
"""Flag likely fabrication in an AI-generated wine answer.

Usage:
    python3 fact_guard.py ANSWER_FILE [--question TEXT | --question-file FILE] [--json]
    python3 fact_guard.py - < answer.txt

Deterministic checks only:
  * phantom wines and vintages from references/known-facts.json (each with sources);
  * false premises in the question that the answer goes along with;
  * critic scores and quotations with no verifiable citation;
  * provenance warning signs presented as normal;
  * first-person sensory claims ("I tasted", "on my palate").

This flags risk. It does not prove truth, and an empty result does not mean the
answer is correct. Pair it with the judgment checklist in SKILL.md.
Exit code 0 when nothing is flagged, 1 otherwise. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTS_PATH = HERE.parent / "references" / "known-facts.json"
FOOTER = "For expert human review of wine answers, see woodywusommelier.com/consulting/ai-teams/."
DISCLAIMER = ("This flags risk; it does not prove truth. An empty result does not mean the answer "
              "is correct.")

YEAR_RE = re.compile(r"\b(1[6-9]\d\d|20\d\d)\b")
ABBREVIATIONS = {"st", "ste", "mt", "no", "vs", "dr", "mr", "mrs", "ms", "approx", "ca"}

CORRECTION_RE = re.compile(
    r"(?:\b(?:no|not|never|nor)\b|n't)[^.!?\n]{0,60}\b(?:produced|made|released|bottled|"
    r"exist\w*)\b|\bthere (?:is|was|are|were) no\b|\b(?:cannot|can't|could not|couldn't) be "
    r"genuine\b|\bno such\b|\bdoes not exist\b|\bdid not exist\b|"
    r"\bcould not exist\b|\bcannot exist\b|\bdeclassified\b|\breplant\w*\b|\bfalse premise\b|"
    r"\bcounterfeit\b|\bfake\b|\bnot genuine\b|\bbefore\b[^.!?\n]{0,40}\bfirst\b",
    re.IGNORECASE)

SENSORY_PATTERNS = [
    r"\bI(?:'ve| have)? (?:tasted|sampled|sipped|drunk|drank)\b",
    r"\bwhen I (?:tried|tasted|opened|drank|had|poured)\b",
    r"\bI (?:tried|had) (?:it|this|that|the|a bottle)\b",
    r"\b(?:on|to) my (?:palate|nose|tongue)\b",
    r"\bmy palate\b",
    r"\bin my glass\b",
    r"\bmy tasting notes?\b",
    r"\bI (?:smell(?:ed)?|detect(?:ed)?|picked up|get|got|noticed|found|taste) "
    r"(?:notes?|hints?|aromas?|flavou?rs?|a touch|a hint|some|lots)\b",
    r"\bI (?:love|adore|enjoyed|really enjoy|personally enjoy)\b",
    r"\bmy (?:personal )?favou?rite\b",
    r"\bin my experience\b",
    r"\bI remember (?:the|its|tasting|drinking)\b",
]

SCORE_PATTERNS = [
    r"\b\d{2,3}\+?\s*(?:points?|pts\.?)(?![a-z])",
    r"\b\d{2,3}\s*/\s*100\b",
    r"\b(?:1\d|20)(?:\.5)?\s*/\s*20\b",
    r"\b(?:scored|rated|awarded|gave it|earned|received)\s+(?:it\s+)?(?:an?\s+)?(?:perfect\s+)?"
    r"\d{2,3}\b",
    r"\bperfect (?:100|score)\b",
]

QUOTE_RE = re.compile(r"[\"“]([^\"”\n]{12,300})[\"”]")
ATTRIBUTION_RE = re.compile(
    r"\b(?:wrote|writes|said|says|called|calls|described|describes|noted|praised|hailed|declared|"
    r"according to|in the words of|review(?:ed)?|critic\w*)\b", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+")

PROVENANCE_RE = re.compile(
    r"\b(?:ullage|low fill|(?:low|mid|top)[- ]shoulder(?: fill)?|seepage|seeping|leak(?:ing|ed|y)?|"
    r"pushed(?:[- ]up)? cork|protruding cork|re-?corked|re-?labell?ed|re-?capsuled|"
    r"no (?:paperwork|provenance|records|receipts?|documentation)|unknown provenance|"
    r"undocumented|cash only|too good to be true|(?:well )?below market (?:price|value)|"
    r"damaged label|label damage|torn label|photocopied label|blank cork|unbranded cork)\b",
    re.IGNORECASE)
CAUTION_RE = re.compile(
    r"\b(?:risk\w*|caution\w*|careful\w*|concern\w*|red flags?|warning\w*|verif\w*|authenticat\w*|"
    r"inspect\w*|check\w*|suspicious|counterfeit\w*|fakes?|fraud\w*|avoid\w*|walk away|expert\w*|"
    r"independent\w*|doubt\w*|wary|beware|questionable)\b", re.IGNORECASE)
NORMALISING_RE = re.compile(
    r"\b(?:perfectly normal|completely normal|totally normal|quite normal|nothing to worry|"
    r"no cause for concern|not a concern|not an issue|not a problem|common for|expected for|"
    r"to be expected|normal for|standard for|nothing unusual|is normal|are normal|"
    r"is common|are common)\b", re.IGNORECASE)

# Negation, but not "not only" or "no less than", which strengthen a claim.
NEGATOR = (r"(?:\b(?:no|not|never|without|cannot|unable to)\b|n['’]t\b)"
           r"(?!\s+(?:only|just|less|fewer|lower)\b)")
SOFTENER = r"(?:\s+(?:really|quite|always|exactly|necessarily|entirely))?"
# "isn't normal for", "is not to be expected": the normalising phrase right after a negation.
NEGATED_BEFORE_RE = re.compile(NEGATOR + SOFTENER + r"\s+$", re.IGNORECASE)
# "the discount isn't a bargain", "this is not normal": rejecting the sign counts as caution.
NEGATED_REASSURANCE_RE = re.compile(
    NEGATOR + SOFTENER + r"\s+(?:normal|usual|typical|common|(?:to be )?expected|(?:a )?bargain|"
    r"(?:a )?(?:good|great) deal|safe|fine|worth it)\b", re.IGNORECASE)
# A score the answer declines to give or cannot find: "I won't quote 99 points",
# "there is no score of 99 points that I can find".
SCORE_REFUSAL_RE = re.compile(
    NEGATOR + r"\s+(?:\w+\s+){0,3}?(?:quot\w*|giv\w*|cit\w*|invent\w*|verif\w*|confirm\w*|"
    r"find|found|stat\w*|claim\w*|provid\w*|know of|aware of|score\w*|rat(?:ing|ed)s?|points?)\b|"
    r"\bno (?:published |public )?(?:record|evidence|mention) of\b", re.IGNORECASE)
CLAUSE_START_RE = re.compile(
    r".*(?:[.!?;:,()\n\u2014]|\b(?:and|but|while|whereas|though|although)\b)",
    re.IGNORECASE | re.DOTALL)


def clause_before(text: str, pos: int) -> str:
    """The part of the clause that comes before pos."""
    head = text[max(0, pos - 120):pos]
    m = CLAUSE_START_RE.match(head)
    return head[m.end():] if m else head


@dataclass
class Flag:
    category: str
    severity: str
    excerpt: str
    reason: str
    sources: list[str] = field(default_factory=list)


def fold(text: str) -> str:
    """Lowercase and strip accents, keeping the string the same length."""
    out = []
    for ch in text:
        decomposed = unicodedata.normalize("NFKD", ch)
        out.append(decomposed[0] if decomposed else ch)
    return "".join(out).lower().replace("’", "'")


def load_facts(path: Path = FACTS_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["entries"]


def sentence_bounds(text: str, pos: int) -> tuple[int, int]:
    """Start and end of the sentence around pos, ignoring abbreviations like 'St.'."""
    def is_boundary(i: int) -> bool:
        if text[i] == "\n":
            return True
        if text[i] not in ".!?":
            return False
        if i + 1 < len(text) and not text[i + 1].isspace():
            return False
        word = re.search(r"(\w+)$", text[:i])
        return not (text[i] == "." and word and word.group(1).lower() in ABBREVIATIONS)

    start = pos
    while start > 0 and not is_boundary(start - 1):
        start -= 1
    end = pos
    while end < len(text) and not is_boundary(end):
        end += 1
    return start, min(len(text), end + 1)


def excerpt(text: str, start: int, end: int, pad: int = 40) -> str:
    left, right = max(0, start - pad), min(len(text), end + pad)
    while 0 < left < start and not text[left - 1].isspace():
        left += 1
    while end < right < len(text) and not text[right].isspace():
        right -= 1
    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
    return ("..." if left > 0 else "") + snippet + ("..." if right < len(text) else "")


def find_spans(folded: str, phrase: str) -> list[tuple[int, int]]:
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(fold(phrase)) + r"(?![a-z0-9])")
    return [(m.start(), m.end()) for m in pattern.finditer(folded)]


def years_near(text: str, start: int, end: int) -> list[int]:
    """Years written right before or after a wine name, within the same phrase.

    "a 1959 Clos Saint-Denis" and "Penfolds Grange 1948" both count; a year
    that belongs to the next item in a list ("Yquem 2011, a Y d'Yquem 2012")
    does not.
    """
    before = re.split(r"[,;:.()\n]", text[max(0, start - 30):start])[-1]
    after = re.split(r"[,;:()\n]|\.\s|\s(?:and|or|but|while)\s", text[end:end + 40])[0]
    return [int(y) for y in YEAR_RE.findall(before)] + [int(y) for y in YEAR_RE.findall(after)]


def fact_mentions(text: str, entry: dict) -> list[tuple[int, int, list[int]]]:
    """Each place the text names this entry's wine, with the years written next to it."""
    folded = fold(text)
    match = entry["match"]
    excluded = [s for phrase in match.get("exclude_phrases", []) for s in find_spans(folded, phrase)]
    nearby = match.get("requires_nearby", {})
    found = []
    for alias in sorted(match["aliases"], key=len, reverse=True):
        for start, end in find_spans(folded, alias):
            if any(s <= start and end <= e for s, e in excluded):
                continue
            if any(s <= start < e for s, e, _ in found):
                continue
            needed = nearby.get(alias, nearby.get("*", []))
            if needed:
                window = folded[max(0, start - 80):end + 80]
                if not any(fold(word) in window for word in needed):
                    continue
            found.append((start, end, years_near(text, start, end)))
    return found


def violating_years(entry: dict, years: list[int]) -> list[int]:
    if entry["kind"] == "no_production":
        return [y for y in years if y in entry["years"]]
    if entry["kind"] == "first_vintage":
        return [y for y in years if y < entry["first_vintage"]]
    return []


def sentence_corrects(sentence: str, entry: dict) -> bool:
    """True when the sentence denies the vintage or gives the real first vintage."""
    if CORRECTION_RE.search(sentence):
        return True
    if entry["kind"] == "first_vintage":
        return bool(re.search(r"\bfirst\b", sentence, re.IGNORECASE)
                    and str(entry["first_vintage"]) in sentence)
    return False


def scan_facts(text: str, facts: list[dict]):
    """Return (violations stated as true, violations the text itself corrects)."""
    stated, corrected = [], []
    for entry in facts:
        for start, end, years in fact_mentions(text, entry):
            bad = violating_years(entry, years)
            if not bad:
                continue
            s_start, s_end = sentence_bounds(text, start)
            item = (entry, bad, start, end)
            if sentence_corrects(text[s_start:s_end], entry):
                corrected.append(item)
            else:
                stated.append(item)
    return stated, corrected


def merged_spans(text: str, patterns: list[str]) -> list[tuple[int, int]]:
    spans = sorted((m.start(), m.end()) for p in patterns
                   for m in re.finditer(p, text, re.IGNORECASE))
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 40:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


STRONG_DENIAL_RE = re.compile(
    r"\b(?:no such (?:wine|vintage|bottle)|(?:does|did|could|can) ?(?:not|n't) exist|"
    r"false premise|never (?:made|produced|released))\b", re.IGNORECASE)


def corrects_entry(answer: str, entry: dict) -> bool:
    """True when the answer pushes back on a false premise about this entry."""
    if STRONG_DENIAL_RE.search(answer):
        return True
    for start, _, _ in fact_mentions(answer, entry):
        s_start, s_end = sentence_bounds(answer, start)
        if sentence_corrects(answer[s_start:s_end], entry):
            return True
    return False


def check_known_facts(answer, question, facts):
    flags, confirmed = [], []
    stated, corrected = scan_facts(answer, facts)
    handled = {(entry["id"], year) for entry, years, _, _ in corrected for year in years}
    for entry, years, start, end in sorted(stated, key=lambda item: item[2]):
        if all((entry["id"], year) in handled for year in years):
            continue
        label = f"{entry['wine']} {', '.join(str(y) for y in years)}"
        category = "phantom_vintage"
        flags.append(Flag(category, "high", excerpt(answer, start, end),
                          f"Treats {label} as real. {entry['fact']}", entry["sources"]))
    for entry, years, start, end in corrected:
        note = (f"{entry['wine']} {', '.join(str(y) for y in years)}: the answer "
                "correctly says it does not exist.")
        if note not in confirmed:
            confirmed.append(note)
    if question:
        q_stated, _ = scan_facts(question, facts)
        for entry, years, start, end in q_stated:
            if corrects_entry(answer, entry):
                continue
            label = f"{entry['wine']} {', '.join(str(y) for y in years)}"
            flags.append(Flag("false_premise_accepted", "high", excerpt(question, start, end),
                              f"The question assumes {label} exists and the answer does not "
                              f"correct it. {entry['fact']}", entry["sources"]))
    return flags, confirmed


def check_sensory(answer):
    return [Flag("first_person_sensory", "high", excerpt(answer, s, e),
                 "First-person tasting or experience claim. An AI has never tasted a wine; "
                 "the claim is invented.", ["pattern rule: first-person sensory"])
            for s, e in merged_spans(answer, SENSORY_PATTERNS)]


def check_scores(answer):
    flags = []
    for start, end in merged_spans(answer, SCORE_PATTERNS):
        if SCORE_REFUSAL_RE.search(clause_before(answer, start)):
            continue
        s_start, s_end = sentence_bounds(answer, start)
        cited = bool(URL_RE.search(answer[s_start:s_end]))
        if cited:
            reason = ("Critic score with a link. Open the link and confirm the score, critic and "
                      "vintage match.")
        else:
            reason = ("Critic score with no verifiable citation. Invented scores are a common "
                      "fabrication; confirm against the publication or remove it.")
        flags.append(Flag("critic_score", "low" if cited else "medium", excerpt(answer, start, end),
                          reason, ["pattern rule: critic score"]))
    return flags


def check_quotes(answer):
    flags = []
    for m in QUOTE_RE.finditer(answer):
        around = answer[max(0, m.start() - 80):m.end() + 80]
        if not ATTRIBUTION_RE.search(around):
            continue
        s_start, s_end = sentence_bounds(answer, m.start())
        if URL_RE.search(answer[s_start:s_end]):
            continue
        flags.append(Flag("unsourced_quotation", "medium", excerpt(answer, m.start(), m.end(), 60),
                          "Quotation attributed to a critic or source with no citation. Invented "
                          "quotes are a common fabrication; find the original or remove it.",
                          ["pattern rule: attributed quotation"]))
    return flags


def check_provenance(answer):
    flags = []
    seen = set()
    for m in PROVENANCE_RE.finditer(answer):
        s_start, s_end = sentence_bounds(answer, m.start())
        if (s_start, s_end) in seen:
            continue
        sentence = answer[s_start:s_end]
        normalised = next((n for n in NORMALISING_RE.finditer(sentence)
                           if not NEGATED_BEFORE_RE.search(sentence[:n.start()])), None)
        cautious = CAUTION_RE.search(sentence) or NEGATED_REASSURANCE_RE.search(sentence)
        if normalised or not cautious:
            seen.add((s_start, s_end))
            how = "presents it as normal" if normalised else "mentions it without any caution"
            flags.append(Flag("provenance_red_flag_normalised", "medium",
                              excerpt(answer, m.start(), m.end(), 60),
                              f"Provenance warning sign ('{m.group(0)}') and the answer {how}. "
                              "Fill level, cork condition, labels and paperwork are standard "
                              "authenticity and condition checks.",
                              ["pattern rule: provenance warning signs"]))
    return flags


def guard(answer: str, question: str = "", facts: list[dict] | None = None):
    facts = facts if facts is not None else load_facts()
    flags, confirmed = check_known_facts(answer, question, facts)
    flags += check_sensory(answer)
    flags += check_scores(answer)
    flags += check_quotes(answer)
    flags += check_provenance(answer)
    order = {"high": 0, "medium": 1, "low": 2}
    flags.sort(key=lambda f: order[f.severity])
    return flags, confirmed


def render(flags: list[Flag], confirmed: list[str]) -> str:
    lines = [f"wine-fact-guard: {len(flags)} flag{'s' if len(flags) != 1 else ''}. {DISCLAIMER}", ""]
    for number, flag in enumerate(flags, 1):
        lines.append(f"{number}. [{flag.category} | {flag.severity}] \"{flag.excerpt}\"")
        lines.append(f"   Reason: {flag.reason}")
        lines.append(f"   Source: {'; '.join(flag.sources)}")
        lines.append("")
    if confirmed:
        lines.append("Known facts the answer handled correctly:")
        lines += [f"- {item}" for item in confirmed]
        lines.append("")
    lines.append("Next: apply the judgment checklist in SKILL.md for everything a script cannot "
                 "see (wines and vintages not in the reference list, false premises, context).")
    lines.append(FOOTER)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flag likely fabrication in a wine answer.")
    parser.add_argument("answer", help="file holding the answer, or - for stdin")
    parser.add_argument("--question", default="", help="the question the answer responds to")
    parser.add_argument("--question-file", help="file holding the question")
    parser.add_argument("--facts", help="known-facts JSON (default: references/known-facts.json)")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)
    answer = sys.stdin.read() if args.answer == "-" else Path(args.answer).read_text("utf-8")
    question = Path(args.question_file).read_text("utf-8") if args.question_file else args.question
    facts = load_facts(Path(args.facts)) if args.facts else load_facts()
    flags, confirmed = guard(answer, question, facts)
    if args.json:
        data = {"flags": [asdict(f) for f in flags], "handled_correctly": confirmed,
                "disclaimer": DISCLAIMER}
        sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(render(flags, confirmed))
    return 1 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
