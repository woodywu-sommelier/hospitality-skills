"""Read a wine list from CSV, TSV or plain text into simple records.

Standard library only. This file is shared by the wine-list-audit and
house-somm skills. Keep the two copies identical: a test checks this.

Plain text lines look like this (commas separate the fields):

    SPARKLING
    Maison Exemple, Brut Tradition, Champagne, NV, $120, glass $24
    Producer, Wine name, Region, 2021, 750ml, $68, cost $22

A line with no price is read as a section header. A header that mentions
"glass" marks the wines under it as by the glass.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

HEADER_ALIASES = {
    "name": {"name", "wine", "wine name", "cuvee", "label", "item", "description"},
    "producer": {"producer", "winery", "domaine", "estate", "maker", "house", "brand"},
    "region": {"region", "appellation", "origin", "country", "area", "aoc", "ava"},
    "vintage": {"vintage", "year", "vin"},
    "format": {"format", "size", "bottle size", "volume", "bottle"},
    "cost": {"cost", "unit cost", "cost price", "wholesale", "landed cost", "bottle cost"},
    "price": {"price", "menu price", "list price", "bottle price", "sell price", "selling price"},
    "glass_price": {"glass price", "btg price", "price per glass", "price glass", "pour price"},
    "btg": {"btg", "by the glass", "glass", "is btg", "pour", "by glass"},
    "type": {"type", "style", "colour", "color", "category", "section"},
    "grape": {"grape", "grapes", "variety", "varietal", "blend", "varieties"},
}

TYPE_WORDS = [
    ("sparkling", ["sparkling", "champagne", "cremant", "cava", "prosecco", "franciacorta",
                   "pet nat", "pet-nat", "petillant", "spumante", "sekt", "mousseux", "bubbles"]),
    ("fortified", ["fortified", "port", "porto", "sherry", "fino", "manzanilla", "amontillado",
                   "oloroso", "madeira", "marsala", "banyuls", "vin doux naturel"]),
    ("sweet", ["sweet", "dessert", "sauternes", "barsac", "tokaji", "late harvest", "icewine",
               "ice wine", "eiswein", "vin santo", "passito", "noble"]),
    ("rose", ["rose", "rosado", "rosato", "pink"]),
    ("orange", ["orange", "skin contact", "skin-contact", "amber", "ramato"]),
    ("white", ["white", "blanc", "bianco", "blanco", "weiss"]),
    ("red", ["red", "rouge", "rosso", "tinto"]),
]

GRAPE_TYPES = {
    "white": ["chardonnay", "sauvignon blanc", "riesling", "chenin", "pinot gris", "pinot grigio",
              "gruner", "albarino", "viognier", "semillon", "gewurztraminer", "muscadet",
              "vermentino", "assyrtiko", "chablis", "sancerre", "verdejo", "godello", "fiano"],
    "red": ["pinot noir", "cabernet", "merlot", "syrah", "shiraz", "grenache", "garnacha",
            "tempranillo", "nebbiolo", "sangiovese", "gamay", "malbec", "zinfandel", "barbera",
            "mourvedre", "rioja", "barolo", "chianti", "beaujolais", "mencia", "carmenere",
            "bordeaux", "cornas", "douro", "nebbiolo"],
}

MONEY_RE = re.compile(r"(?:[$€£]\s?)(\d{1,5}(?:[.,]\d{2})?)")
YEAR_RE = re.compile(r"\b(18[89]\d|19\d\d|20\d\d)\b")
NV_RE = re.compile(r"\b(nv|n\.v\.|non[- ]vintage)\b", re.IGNORECASE)
FORMAT_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s?(ml|cl|l|ltr|litre|liter)\b", re.IGNORECASE)
FORMAT_WORDS = {"half bottle": 375, "half": 375, "demi": 375, "magnum": 1500, "split": 187,
                "piccolo": 187, "double magnum": 3000}
COST_RE = re.compile(r"\bcost[:\s]*[$€£]?\s?(\d{1,5}(?:[.,]\d{2})?)", re.IGNORECASE)
GLASS_RE = re.compile(r"\b(?:glass|gl|btg)[:\s]*[$€£]?\s?(\d{1,4}(?:[.,]\d{2})?)", re.IGNORECASE)
SLASH_PRICES_RE = re.compile(r"[$€£]?\s?(\d{1,4}(?:[.,]\d{2})?)\s*/\s*[$€£]?\s?(\d{1,5}(?:[.,]\d{2})?)")
BARE_NUMBER_RE = re.compile(r"(?<![\w.])(\d{1,5}(?:[.,]\d{2})?)(?![\w.])")


def fold(text: str) -> str:
    """Lowercase and strip accents, keeping the string the same length."""
    out = []
    for ch in text:
        decomposed = unicodedata.normalize("NFKD", ch)
        out.append(decomposed[0] if decomposed else ch)
    return "".join(out).lower()


def has_word(haystack: str, word: str) -> bool:
    return re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", haystack) is not None


@dataclass
class Wine:
    line_no: int
    raw: str
    name: str = ""
    producer: str = ""
    region: str = ""
    vintage: str = ""
    format_raw: str = ""
    format_ml: int | None = None
    cost: float | None = None
    price: float | None = None
    glass_price: float | None = None
    btg: bool = False
    type: str = ""
    grape: str = ""
    section: str = ""
    problems: list[str] = field(default_factory=list)

    def label(self) -> str:
        parts = [p for p in (self.producer, self.name) if p]
        text = ", ".join(parts) if parts else self.raw.strip()
        if self.vintage:
            text += " " + self.vintage
        if self.format_ml and self.format_ml != 750:
            text += f" ({self.format_ml} ml)"
        return text

    def size_ml(self) -> int:
        return self.format_ml or 750

    def search_text(self) -> str:
        return fold(" ".join([self.producer, self.name, self.region, self.grape, self.type,
                              self.section]))


@dataclass
class WineList:
    wines: list[Wine]
    source_format: str
    unused_columns: list[str] = field(default_factory=list)
    skipped_lines: list[tuple[int, str]] = field(default_factory=list)


def parse_money(value: str) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace("$", "").replace("€", "").replace("£", "").strip()
    if not text:
        return None
    text = text.replace(",", ".") if re.fullmatch(r"\d+,\d{2}", text) else text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def parse_format(text: str) -> int | None:
    if not text:
        return None
    match = FORMAT_RE.search(text)
    if match:
        amount = float(match.group(1).replace(",", "."))
        unit = match.group(2).lower()
        if unit == "ml":
            return int(round(amount))
        if unit == "cl":
            return int(round(amount * 10))
        return int(round(amount * 1000))
    folded = fold(text)
    for word, ml in sorted(FORMAT_WORDS.items(), key=lambda kv: -len(kv[0])):
        if has_word(folded, word):
            return ml
    return None


def format_notation(text: str) -> str:
    """Return the unit style a format was written in, for consistency checks."""
    match = FORMAT_RE.search(text or "")
    if match:
        unit = match.group(2).lower()
        return {"ltr": "l", "litre": "l", "liter": "l"}.get(unit, unit)
    return "word" if text else ""


def parse_bool(value: str) -> tuple[bool, float | None]:
    """Read a by-the-glass cell. A number counts as yes plus a glass price."""
    text = fold(str(value or "").strip())
    if not text:
        return False, None
    number = parse_money(text)
    if number is not None:
        return number > 0, number if number > 1 else None
    return text in {"y", "yes", "true", "x", "btg", "glass", "by the glass", "1"}, None


def infer_type(*texts: str) -> str:
    folded = fold(" ".join(t for t in texts if t))
    for type_name, words in TYPE_WORDS:
        if any(has_word(folded, w) for w in words):
            return type_name
    for type_name, words in GRAPE_TYPES.items():
        if any(has_word(folded, w) for w in words):
            return type_name
    return ""


def normalise_type(text: str) -> str:
    return infer_type(text) if text else ""


def _canonical_header(header: str) -> str | None:
    key = re.sub(r"[_\-]+", " ", fold(header).strip())
    key = re.sub(r"[^a-z ]", "", key).strip()
    key = re.sub(r"\s+", " ", key)
    for field_name, aliases in HEADER_ALIASES.items():
        if key in aliases:
            return field_name
    return None


def _looks_delimited(first_line: str) -> bool:
    if not any(d in first_line for d in (",", "\t", ";", "|")):
        return False
    cells = re.split(r"[,\t;|]", first_line)
    fields = {_canonical_header(c) for c in cells}
    return "price" in fields and ("name" in fields or "producer" in fields)


def _finish(wine: Wine, current_year: int | None) -> None:
    if not wine.name and not wine.producer:
        wine.problems.append("no wine name")
    if wine.price is None and wine.glass_price is None:
        wine.problems.append("no menu price")
    if wine.btg and wine.glass_price is None:
        wine.problems.append("marked by the glass but no glass price")
    if wine.cost is not None and wine.price is not None and wine.cost >= wine.price:
        wine.problems.append("cost is equal to or above the menu price")
    if (wine.glass_price is not None and wine.price is not None
            and wine.glass_price >= wine.price):
        wine.problems.append("glass price is equal to or above the bottle price")
    if not wine.type:
        wine.type = infer_type(wine.section, wine.name, wine.region, wine.grape, wine.producer)


def parse_delimited(text: str, current_year: int | None = None) -> WineList:
    lines = text.splitlines()
    header_line = next(line for line in lines if line.strip())
    try:
        dialect = csv.Sniffer().sniff(header_line, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    start = next(i for i, row in enumerate(rows) if any(cell.strip() for cell in row))
    headers = rows[start]
    mapping: dict[int, str] = {}
    unused = []
    for index, header in enumerate(headers):
        canonical = _canonical_header(header)
        if canonical and canonical not in mapping.values():
            mapping[index] = canonical
        elif header.strip():
            unused.append(header.strip())
    wines = []
    for offset, row in enumerate(rows[start + 1:], start=start + 2):
        if not any(cell.strip() for cell in row):
            continue
        if row and row[0].lstrip().startswith("#"):
            continue
        values = {mapping[i]: row[i].strip() for i in mapping if i < len(row)}
        wine = Wine(line_no=offset, raw=delimiter.join(row))
        wine.name = values.get("name", "")
        wine.producer = values.get("producer", "")
        wine.region = values.get("region", "")
        wine.grape = values.get("grape", "")
        vintage = values.get("vintage", "")
        if NV_RE.search(vintage):
            wine.vintage = "NV"
        elif YEAR_RE.fullmatch(vintage.strip()):
            wine.vintage = vintage.strip()
        elif vintage:
            wine.vintage = vintage
            wine.problems.append(f"vintage not readable: {vintage!r}")
        wine.format_raw = values.get("format", "")
        wine.format_ml = parse_format(wine.format_raw)
        if wine.format_raw and wine.format_ml is None:
            wine.problems.append(f"format not readable: {wine.format_raw!r}")
        for key in ("cost", "price", "glass_price"):
            raw_value = values.get(key, "")
            number = parse_money(raw_value)
            if raw_value and number is None:
                wine.problems.append(f"{key.replace('_', ' ')} not a number: {raw_value!r}")
            setattr(wine, key, number)
        btg, glass_from_flag = parse_bool(values.get("btg", ""))
        wine.btg = btg or wine.glass_price is not None
        if wine.glass_price is None and glass_from_flag is not None:
            wine.glass_price = glass_from_flag
        wine.type = normalise_type(values.get("type", ""))
        wine.section = values.get("type", "")
        _finish(wine, current_year)
        wines.append(wine)
    return WineList(wines=wines, source_format="delimited", unused_columns=unused)


def _is_header(line: str) -> bool:
    """A line with no price and no commas is a section header."""
    if "," in line or "|" in line or "\t" in line:
        return False
    return not (MONEY_RE.search(line) or BARE_NUMBER_RE.search(YEAR_RE.sub("", line)))


def parse_text_line(line: str, line_no: int, section: str, section_btg: bool) -> Wine:
    wine = Wine(line_no=line_no, raw=line, section=section, btg=section_btg)
    work = line
    match = COST_RE.search(work)
    if match:
        wine.cost = parse_money(match.group(1))
        work = work[:match.start()] + work[match.end():]
    match = GLASS_RE.search(work)
    if match:
        wine.glass_price = parse_money(match.group(1))
        wine.btg = True
        work = work[:match.start()] + work[match.end():]
    elif re.search(r"\bbtg\b", work, re.IGNORECASE):
        wine.btg = True
        work = re.sub(r"\bbtg\b", "", work, flags=re.IGNORECASE)
    match = FORMAT_RE.search(work)
    if match:
        wine.format_raw = match.group(0)
        wine.format_ml = parse_format(match.group(0))
        work = work[:match.start()] + work[match.end():]
    else:
        folded = fold(work)
        for word in sorted(FORMAT_WORDS, key=len, reverse=True):
            found = re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", folded)
            if found:
                wine.format_raw = work[found.start():found.end()]
                wine.format_ml = FORMAT_WORDS[word]
                work = work[:found.start()] + work[found.end():]
                break
    match = SLASH_PRICES_RE.search(work)
    if match and section_btg and wine.glass_price is None:
        wine.glass_price = parse_money(match.group(1))
        wine.price = parse_money(match.group(2))
        wine.btg = True
        work = work[:match.start()] + work[match.end():]
    else:
        monies = list(MONEY_RE.finditer(work))
        if monies:
            last = monies[-1]
            amount = parse_money(last.group(1))
            if section_btg and wine.glass_price is None and len(monies) == 1:
                wine.glass_price = amount
            else:
                wine.price = amount
            work = work[:last.start()] + work[last.end():]
    nv = NV_RE.search(work)
    years = list(YEAR_RE.finditer(work))
    if nv:
        wine.vintage = "NV"
        work = work[:nv.start()] + work[nv.end():]
    elif years:
        wine.vintage = years[-1].group(1)
        work = work[:years[-1].start()] + work[years[-1].end():]
    if wine.price is None and wine.glass_price is None:
        bare = list(BARE_NUMBER_RE.finditer(work))
        if bare:
            amount = parse_money(bare[-1].group(1))
            if section_btg:
                wine.glass_price = amount
            else:
                wine.price = amount
            work = work[:bare[-1].start()] + work[bare[-1].end():]
    parts = [p.strip(" \t-:|·") for p in re.split(r"[,|\t·]", work)]
    parts = [p for p in parts if p]
    if len(parts) == 1:
        wine.name = parts[0]
    elif len(parts) == 2:
        wine.producer, wine.name = parts
    elif len(parts) >= 3:
        wine.producer, wine.name = parts[0], parts[1]
        wine.region = ", ".join(parts[2:])
    return wine


def parse_text(text: str, current_year: int | None = None) -> WineList:
    wines = []
    skipped = []
    section = ""
    section_btg = False
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if _is_header(line):
            if len(line) <= 60:
                section = line.rstrip(":").strip()
                section_btg = "glass" in fold(section) or has_word(fold(section), "btg")
            else:
                skipped.append((line_no, line))
            continue
        wine = parse_text_line(line, line_no, section, section_btg)
        if section_btg:
            wine.btg = True
        _finish(wine, current_year)
        wines.append(wine)
    return WineList(wines=wines, source_format="text", skipped_lines=skipped)


def parse_wine_list(text: str, current_year: int | None = None) -> WineList:
    text = text.lstrip("﻿")
    first = next((line for line in text.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")), "")
    if _looks_delimited(first):
        body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        return parse_delimited(body, current_year)
    return parse_text(text, current_year)


def load_wine_list(path: str | Path, current_year: int | None = None) -> WineList:
    return parse_wine_list(Path(path).read_text(encoding="utf-8-sig"), current_year)
