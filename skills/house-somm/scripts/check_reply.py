#!/usr/bin/env python3
"""Check a wine assistant's reply against the venue's own wine list.

Usage:
    python3 check_reply.py --list LIST [--reply REPLY_FILE] [--guest "guest message"] [--json]

The reply is read from --reply or from stdin. The script:
  * finds every list wine the reply names and checks the vintage and price
    quoted next to it against the list line;
  * flags wine-like names (a producer word, or a capitalised name next to a
    vintage) that do not match anything on the list;
  * flags first-person sensory claims ("I tasted", "on my palate");
  * flags a missing human hand-off for allergies, off bottles and bottles at
    or above the venue's high-value threshold;
  * flags phrases that push guests to drink more.

It is a safety net, not proof: a clean result means nothing was caught, not
that the reply is perfect. Exit code 0 when nothing is flagged, 1 otherwise.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from winelist import MONEY_RE, Wine, fold, load_wine_list, parse_money  # noqa: E402

REFERENCES = HERE.parent / "references"

PRODUCER_WORDS = (r"Ch[aâ]teau|Domaine|Maison|Bodegas?|Weingut|Tenuta|Clos|Quinta|Cantina|Schloss|"
                  r"Castello|Fattoria|Podere|Caves?|Celler|Cellier|Herdade|Azienda")
PARTICLES = r"(?:de|du|des|la|le|les|di|del|della|von|vom|da|do|dos|d'|l')"
CAP = r"[A-ZÀ-ÖØ-Þ][\w'’-]*"
PATTERN_PRODUCER = re.compile(
    rf"\b(?:{PRODUCER_WORDS})\s+(?:{PARTICLES}\s*)*{CAP}(?:\s+(?:{PARTICLES}\s*)*{CAP}){{0,3}}")
PATTERN_ESTATE = re.compile(rf"(?:{CAP}\s+){{1,3}}(?:Cellars|Winery|Vineyards?|Estates?|Wines)\b")
PATTERN_NAME_YEAR = re.compile(rf"((?:{CAP}\s+){{1,5}})((?:19|20)\d\d)\b")
PATTERN_YEAR_NAME = re.compile(rf"\b((?:19|20)\d\d)\s+((?:{CAP}\s?){{1,5}})")
YEAR_RE = re.compile(r"\b((?:19|20)\d\d)\b")
NV_RE = re.compile(r"\b(?:NV|N\.V\.|non-vintage)\b", re.IGNORECASE)

STOPWORDS = {
    "the", "a", "an", "in", "from", "for", "since", "this", "that", "these", "our", "your", "its",
    "with", "and", "or", "if", "try", "pair", "consider", "vintage", "bottle", "glass", "by",
    "of", "on", "at", "to", "my", "we", "i", "it", "is", "as", "both", "either", "also", "then",
    "january", "february", "march", "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "spring", "summer", "autumn", "fall", "winter", "since",
    "until", "before", "after", "around", "about", "under", "over", "closest", "option", "note",
    "list", "line", "here", "there", "what", "which", "would", "could", "should", "good",
    "great", "lovely", "nice", "classic", "harvested", "made", "bottled", "released",
}

SENSORY_PATTERNS = [
    r"\bI(?:'ve| have)? (?:tasted|sampled|sipped|drunk|drank)\b",
    r"\bwhen I (?:tried|tasted|opened|drank|had|poured)\b",
    r"\bI (?:tried|had) (?:it|this|that|the)\b",
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

PUSH_PATTERNS = [
    r"\banother (?:bottle|round)\b",
    r"\bone more (?:glass|bottle|round)\b",
    r"\bdrink up\b",
    r"\bkeep (?:the|it|your) (?:wine|glasses?|night|evening) (?:flowing|going|topped)\b",
    r"\bwhy not (?:a second|another)\b",
    r"\bbottomless\b",
]

ALLERGY_RE = re.compile(r"\b(?:allerg\w*|intoleran\w*|sulph?ites?|sulfites?|histamines?|"
                        r"coeliac|celiac|anaphyla\w*)\b", re.IGNORECASE)
OFF_BOTTLE_RE = re.compile(r"\b(?:corked|cork taint|tca|faulty|flawed|spoiled|oxidi[sz]ed|"
                           r"tastes? (?:off|wrong|weird|strange)|smells? (?:off|wrong|musty|"
                           r"like (?:vinegar|wet cardboard))|gone off|is off|bad bottle)\b",
                           re.IGNORECASE)


@dataclass
class Flag:
    kind: str
    excerpt: str
    reason: str


@dataclass
class Match:
    wine: str
    list_line: int
    bottle_price: float | None
    glass_price: float | None
    vintage: str
    start: int = field(repr=False, default=0)
    end: int = field(repr=False, default=0)


def find_word(haystack: str, needle: str) -> list[tuple[int, int]]:
    if not needle:
        return []
    pattern = re.compile(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])")
    return [(m.start(), m.end()) for m in pattern.finditer(haystack)]


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", fold(text)).strip()


def clause_end(text: str, start: int, stop: int) -> int:
    """End of the sentence or line that starts at start, capped at stop."""
    match = re.compile(r"(?<!\bSt)(?<!\bNo)[.!?](?:\s|$)|\n").search(text, start)
    end = match.start() if match else len(text)
    return min(end, stop, start + 160)


def excerpt(text: str, start: int, end: int) -> str:
    """Text between start and end, trimmed so it never starts or ends mid-word."""
    while 0 < start < end and not text[start - 1].isspace():
        start += 1
    while start < end < len(text) and not text[end].isspace() and text[end] not in ".,;!?":
        end -= 1
    return re.sub(r"\s+", " ", text[start:end]).strip()


def distinctive_names(wines: list[Wine]) -> set[str]:
    generic = {"brut", "reserve", "reserva", "riserva", "rosso", "bianco", "blanco", "rouge",
               "blanc", "red", "white", "rose", "grand vin", "cuvee", "classico", "crianza",
               "kabinett", "estate", "house red", "house white"}
    names = [norm(w.name) for w in wines if w.name]
    grapes = {norm(w.grape) for w in wines if w.grape}
    return {n for n in names if names.count(n) == 1 and len(n) >= 6 and n not in generic
            and n not in grapes}


def locate_list_wines(reply: str, wines: list[Wine]) -> list[tuple[int, int, list[Wine]]]:
    """Return (start, end, candidate wines) for each place the reply names a list wine."""
    folded = fold(reply)
    mentions: list[tuple[int, int, list[Wine]]] = []
    by_producer: dict[str, list[Wine]] = {}
    for wine in wines:
        if wine.producer and len(norm(wine.producer)) >= 4:
            by_producer.setdefault(norm(wine.producer), []).append(wine)
    for producer, group in by_producer.items():
        for start, end in find_word(folded, producer):
            window_end = clause_end(reply, end, len(reply))
            window = folded[end:window_end]
            named = [w for w in group if w.name and norm(w.name) in window]
            if named:
                longest = max(len(norm(w.name)) for w in named)
                named = [w for w in named if len(norm(w.name)) == longest]
                name_pos = window.find(norm(named[0].name))
                end = end + name_pos + len(norm(named[0].name))
            mentions.append((start, end, named or group))
    distinctive = distinctive_names(wines)
    for wine in wines:
        name = norm(wine.name)
        if name not in distinctive:
            continue
        for start, end in find_word(folded, name):
            if any(s <= start < e or s < end <= e for s, e, _ in mentions):
                continue
            mentions.append((start, end, [wine]))
    mentions.sort(key=lambda m: m[0])
    merged: list[tuple[int, int, list[Wine]]] = []
    for mention in mentions:
        if merged and mention[0] < merged[-1][1]:
            continue
        merged.append(mention)
    return merged


def amounts_in(text: str, budget_words: list[str]) -> list[float]:
    found = []
    for match in MONEY_RE.finditer(text):
        before = fold(text[max(0, match.start() - 14):match.start()])
        if any(re.search(r"\b" + re.escape(w) + r"\s*$", before) for w in budget_words):
            continue
        value = parse_money(match.group(1))
        if value is not None:
            found.append(value)
    return found


def check_list_mentions(reply, mentions, settings):
    flags, matches = [], []
    for index, (start, end, candidates) in enumerate(mentions):
        stop = mentions[index + 1][0] if index + 1 < len(mentions) else len(reply)
        context_end = clause_end(reply, end, stop)
        context = reply[start:context_end]
        after = reply[end:context_end]
        label = candidates[0].label() if len(candidates) == 1 else (
            f"{candidates[0].producer} (one of {len(candidates)} wines from this producer)")
        vintages = {w.vintage for w in candidates}
        years = YEAR_RE.findall(after)
        wrong_years = [y for y in years if y not in vintages]
        if wrong_years:
            flags.append(Flag("vintage_mismatch", excerpt(reply, start, context_end),
                              f"Reply gives {', '.join(wrong_years)} for {label}; the list has "
                              f"{', '.join(sorted(v or 'no vintage' for v in vintages))}."))
        prices = {p for w in candidates for p in (w.price, w.glass_price) if p is not None}
        amounts = amounts_in(after, settings["budget_words_before_amounts"])
        wrong_prices = [a for a in amounts if a not in prices]
        if wrong_prices:
            listed = ", ".join(f"{settings['currency_symbol']}{p:g}" for p in sorted(prices))
            shown = ", ".join(f"{settings['currency_symbol']}{a:g}" for a in wrong_prices)
            flags.append(Flag("price_mismatch", excerpt(reply, start, context_end),
                              f"Reply quotes {shown} for {label}; the list has {listed or 'no price'}."))
        if len(candidates) == 1:
            wine = candidates[0]
            missing = []
            has_vintage = (wine.vintage in years or (wine.vintage == "NV" and NV_RE.search(after)))
            if wine.vintage and not has_vintage and not wrong_years:
                missing.append("vintage")
            if prices and not amounts and not wrong_prices:
                missing.append("price")
            if missing:
                flags.append(Flag("incomplete_quote", excerpt(reply, start, context_end),
                                  f"Names {wine.label()} without its {' or '.join(missing)} "
                                  "from the list line."))
            matches.append(Match(wine.label(), wine.line_no, wine.price, wine.glass_price,
                                 wine.vintage, start, end))
        else:
            for wine in candidates:
                matches.append(Match(wine.label(), wine.line_no, wine.price, wine.glass_price,
                                     wine.vintage, start, end))
    return flags, matches


def strip_stopwords(words: list[str]) -> list[str]:
    while words and fold(words[0]).strip(".,'’") in STOPWORDS:
        words = words[1:]
    while words and fold(words[-1]).strip(".,'’") in STOPWORDS:
        words = words[:-1]
    return words


def resembles_list_wine(candidate: str, year: str | None, wines: list[Wine]) -> bool:
    text = norm(candidate)
    distinctive = distinctive_names(wines)
    for wine in wines:
        producer = norm(wine.producer)
        if producer and len(producer) >= 4 and (producer in text or text in producer):
            return True
        name = norm(wine.name)
        if name in distinctive and name in text:
            return True
        if year and wine.vintage == year:
            for field_text in (wine.region, wine.grape, wine.name):
                value = norm(field_text)
                if value and len(value) >= 4 and (value in text or text in value):
                    return True
    return False


def check_unknown_wines(reply, mentions, wines):
    flags = []
    covered = [(s, e) for s, e, _ in mentions]
    seen = set()

    def overlaps(start, end):
        return any(s < end and start < e for s, e in covered)

    candidates = []
    for pattern in (PATTERN_PRODUCER, PATTERN_ESTATE):
        for m in pattern.finditer(reply):
            year = YEAR_RE.search(reply[m.end():m.end() + 8])
            candidates.append((m.start(), m.end(), m.group(0), year.group(1) if year else None))
    for m in PATTERN_NAME_YEAR.finditer(reply):
        words = strip_stopwords(m.group(1).split())
        if words:
            text = " ".join(words)
            start = m.start(1) + m.group(1).find(words[0])
            candidates.append((start, m.end(), f"{text} {m.group(2)}", m.group(2)))
    for m in PATTERN_YEAR_NAME.finditer(reply):
        words = strip_stopwords(m.group(2).split())
        if words:
            candidates.append((m.start(), m.end(), f"{m.group(1)} {' '.join(words)}", m.group(1)))
    for start, end, text, year in sorted(candidates):
        if overlaps(start, end):
            continue
        key = norm(text)
        if key in seen:
            continue
        seen.add(key)
        if resembles_list_wine(text, year, wines):
            continue
        covered.append((start, end))
        flags.append(Flag("not_on_list", text.strip(),
                          "Could not find this wine on the list. Remove it, or check the list "
                          "by hand if it is a spelling difference."))
    return flags


def check_patterns(reply, patterns, kind, reason):
    """One flag per passage, however many patterns hit it."""
    spans = sorted((m.start(), m.end()) for pattern in patterns
                   for m in re.finditer(pattern, reply, re.IGNORECASE))
    merged: list[list[int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + 30:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [Flag(kind, excerpt(reply, max(0, start - 30), min(len(reply), end + 30)), reason)
            for start, end in merged]


def check_escalation(reply, guest, matches, settings):
    flags = []
    handoff = re.compile("|".join(settings["handoff_patterns"]), re.IGNORECASE)
    has_handoff = bool(handoff.search(reply))
    threshold = settings["escalate_at_or_above_bottle_price"]
    sym = settings["currency_symbol"]
    expensive = [m for m in matches if m.bottle_price is not None and m.bottle_price >= threshold]
    if expensive and not has_handoff:
        flags.append(Flag("escalation_missing", expensive[0].wine,
                          f"Bottle at or above {sym}{threshold:g} recommended with no offer to "
                          "bring in the sommelier or a member of the team."))
    both = f"{guest}\n{reply}"
    if ALLERGY_RE.search(both) and not has_handoff:
        flags.append(Flag("escalation_missing", ALLERGY_RE.search(both).group(0),
                          "Allergy or intolerance mentioned; the reply must hand over to a person "
                          "and not give medical or ingredient assurances."))
    if guest and OFF_BOTTLE_RE.search(guest) and not has_handoff:
        flags.append(Flag("escalation_missing", OFF_BOTTLE_RE.search(guest).group(0),
                          "Guest reports a possibly faulty bottle; the reply must bring a person "
                          "to the table."))
    return flags


def check_reply(reply: str, wines: list[Wine], guest: str = "", settings: dict | None = None):
    settings = settings or json.loads((REFERENCES / "house-settings.json").read_text("utf-8"))
    mentions = locate_list_wines(reply, wines)
    flags, matches = check_list_mentions(reply, mentions, settings)
    flags += check_unknown_wines(reply, mentions, wines)
    flags += check_patterns(reply, SENSORY_PATTERNS, "sensory_claim",
                            "First-person tasting or experience claim. The assistant has never "
                            "tasted anything; describe the wine from the list or producer notes.")
    flags += check_patterns(reply, PUSH_PATTERNS, "pushes_drinking",
                            "Phrase that nudges the guest to drink more. Offer, never push.")
    flags += check_escalation(reply, guest, matches, settings)
    return flags, matches


def render(flags: list[Flag], matches: list[Match], list_size: int) -> str:
    lines = [f"check_reply: {len(flags)} flag{'s' if len(flags) != 1 else ''} "
             f"(checked against {list_size} list entries)", ""]
    lines.append("Matched to the list:")
    if matches:
        seen = set()
        for m in matches:
            if (m.wine, m.list_line) in seen:
                continue
            seen.add((m.wine, m.list_line))
            prices = []
            if m.bottle_price is not None:
                prices.append(f"bottle ${m.bottle_price:g}")
            if m.glass_price is not None:
                prices.append(f"glass ${m.glass_price:g}")
            lines.append(f"  - {m.wine} ({', '.join(prices) or 'no price'}), list line {m.list_line}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("Flags:")
    if not flags:
        lines.append("  (none) Nothing was caught, which is not the same as proof the reply is right.")
    for number, flag in enumerate(flags, 1):
        lines.append(f"  {number}. [{flag.kind}] \"{flag.excerpt}\"")
        lines.append(f"     {flag.reason}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a wine reply against the venue's list.")
    parser.add_argument("--list", required=True, help="wine list file (CSV, TSV or text)")
    parser.add_argument("--reply", help="file holding the reply (default: stdin)")
    parser.add_argument("--guest", default="", help="the guest's message, for escalation checks")
    parser.add_argument("--settings", help="settings JSON (default: references/house-settings.json)")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)
    wines = load_wine_list(args.list).wines
    reply = Path(args.reply).read_text(encoding="utf-8") if args.reply else sys.stdin.read()
    settings = json.loads(Path(args.settings).read_text("utf-8")) if args.settings else None
    flags, matches = check_reply(reply, wines, args.guest, settings)
    if args.json:
        data = {"flags": [asdict(f) for f in flags],
                "matched": [{k: v for k, v in asdict(m).items() if k not in ("start", "end")}
                            for m in matches]}
        sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(render(flags, matches, len(wines)))
    return 1 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
