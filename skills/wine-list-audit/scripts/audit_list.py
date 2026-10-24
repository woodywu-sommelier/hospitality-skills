#!/usr/bin/env python3
"""Audit a restaurant wine list and print a short ranked report.

Usage:
    python3 audit_list.py LIST [--menu MENU] [--config JSON] [--year YYYY] [--json]

LIST is a CSV, TSV or plain text file, or "-" to read pasted text from stdin.
Standard library only. The script never invents costs, prices or sales: every
number in the report is either read from your files or computed from them.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from winelist import Wine, WineList, fold, format_notation, has_word, parse_wine_list  # noqa: E402

REFERENCES = HERE.parent / "references"
CLOSING_LINE = "For a full Service Audit, see woodywusommelier.com/consulting/."

FIX, LOOK, FINE = "fix", "look", "fine"
GROUP_NAMES = {
    "sparkling": "sparkling wines", "white": "whites", "rose": "rosés", "orange": "orange wines",
    "red": "reds", "sweet": "sweet wines", "fortified": "fortified wines", "": "bottles",
}
SINGULAR = {
    "sparkling": "sparkling wine", "white": "white", "rose": "rosé", "orange": "orange wine",
    "red": "red", "sweet": "sweet wine", "fortified": "fortified wine", "": "bottle",
}
COMPATIBLE_STYLES = {
    "red": {"light_red", "medium_red", "structured_red"},
    "white": {"crisp_white", "aromatic_white", "full_white"},
    "rose": {"rose"},
    "sparkling": {"sparkling"},
    "orange": {"orange"},
    "sweet": {"sweet"},
    "fortified": {"fortified", "sweet"},
}
STYLE_NAMES = {
    "sparkling": "sparkling", "crisp_white": "crisp white", "aromatic_white": "aromatic white",
    "full_white": "fuller white", "rose": "rosé", "orange": "orange", "light_red": "light red",
    "medium_red": "medium red", "structured_red": "structured red", "sweet": "sweet",
    "fortified": "fortified",
}


@dataclass
class Finding:
    level: str
    check: str
    title: str
    lines: list[str] = field(default_factory=list)
    impact: str = ""
    weight: float = 0.0


@dataclass
class Report:
    title: str
    summary: str
    findings: list[Finding]
    missing: list[str]

    def by_level(self, level: str) -> list[Finding]:
        items = [f for f in self.findings if f.level == level]
        return sorted(items, key=lambda f: -f.weight)


def join_or(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " or " + items[-1]


def count(number: int, singular: str, plural: str | None = None) -> str:
    return f"{number} {singular if number == 1 else (plural or singular + 's')}"


def money(value: float, symbol: str = "$") -> str:
    if abs(value - round(value)) < 0.005:
        return f"{symbol}{int(round(value))}"
    return f"{symbol}{value:.2f}"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_standard_bottle(wine: Wine) -> bool:
    return wine.price is not None and wine.size_ml() == 750


def bottle_entries(wines: list[Wine]) -> list[Wine]:
    """Standard bottles, counting a wine once when it appears in both a glass
    section and a bottle section."""
    bottles = [w for w in wines if is_standard_bottle(w)]
    listed = {(fold(w.producer), fold(w.name), w.vintage) for w in bottles if not w.btg}
    return [w for w in bottles
            if not w.btg or (fold(w.producer), fold(w.name), w.vintage) not in listed]


def priced_bottles(wines: list[Wine]) -> list[Wine]:
    return [w for w in wines if w.price is not None]


def band_for(cost: float, bands: list[dict]) -> dict:
    for band in bands:
        if band["cost_up_to"] is None or cost <= band["cost_up_to"]:
            return band
    return bands[-1]


def margin_pct(wine: Wine) -> float:
    return (wine.price - wine.cost) / wine.price * 100


def valid_cost(wine: Wine) -> bool:
    return wine.cost is not None and wine.price is not None and 0 < wine.cost < wine.price


def type_groups(wines: list[Wine], minimum: int) -> dict[str, list[Wine]]:
    """Group bottles by type when types are known, otherwise use the whole list."""
    typed: dict[str, list[Wine]] = {}
    for wine in wines:
        if wine.type:
            typed.setdefault(wine.type, []).append(wine)
    if sum(1 for group in typed.values() if len(group) >= minimum) >= 2:
        return {k: v for k, v in typed.items() if len(v) >= minimum}
    return {"": wines} if len(wines) >= minimum else {}


def trimmed(lines: list[str], limit: int) -> list[str]:
    if len(lines) <= limit:
        return lines
    return lines[:limit] + [f"...and {len(lines) - limit} more (run with --all to see every line)."]


# Checks ---------------------------------------------------------------------

def check_markups(wines, cfg, sym, limit):
    findings, missing = [], []
    bands = cfg["bottle_markup_bands"]["bands"]
    bottles = priced_bottles(wines)
    costed = [w for w in bottles if valid_cost(w)]
    below, above = [], []
    for wine in costed:
        band = band_for(wine.cost, bands)
        multiple = wine.price / wine.cost
        if multiple < band["low"]:
            target = wine.cost * band["low"]
            below.append((target - wine.price, wine, multiple, band, target))
        elif multiple > band["high"]:
            above.append((multiple - band["high"], wine, multiple, band))
    if below:
        below.sort(key=lambda item: -item[0])
        lines = [f"{w.label()}: cost {money(w.cost, sym)}, price {money(w.price, sym)}, "
                 f"{m:.2f}x (your band {b['low']:.1f}x to {b['high']:.1f}x). At {b['low']:.1f}x "
                 f"the price would be {money(t, sym)}, {money(gap, sym)} more per bottle sold."
                 for gap, w, m, b, t in below]
        findings.append(Finding(
            FIX, "markup", f"{count(len(below), 'bottle')} priced below your markup band",
            trimmed(lines, limit),
            "Margin is given away on every one of these bottles sold. No sales volumes were "
            "supplied, so only the gap per bottle is shown, not a total.",
            80 + min(below[0][0], 100) / 10))
    if above:
        above.sort(key=lambda item: -item[0])
        lines = [f"{w.label()}: cost {money(w.cost, sym)}, price {money(w.price, sym)}, "
                 f"{m:.2f}x (your band {b['low']:.1f}x to {b['high']:.1f}x)."
                 for _, w, m, b in above]
        findings.append(Finding(
            LOOK, "markup", f"{count(len(above), 'bottle')} priced above your markup band",
            trimmed(lines, limit),
            "Guests who know retail prices may read these as poor value, which can slow sales. "
            "Without sales data this is a risk, not a measured loss.", 40))
    inside = len(costed) - len(below) - len(above)
    if costed and inside:
        findings.append(Finding(FINE, "markup",
                                f"{inside} of {len(costed)} costed bottles sit inside your markup bands."))
    uncosted = [w for w in bottles if w.cost is None]
    if not costed:
        missing.append("No costs were supplied, so markups and margins were not checked. "
                       "Add a cost column (or 'cost $NN' on each line) to check them.")
    elif uncosted:
        missing.append(f"Cost was not supplied for {len(uncosted)} of {len(bottles)} bottles, "
                       "so their markups were not checked.")
    return findings, missing


def check_glass_pricing(wines, cfg, sym, limit):
    findings = []
    glass_cfg = cfg["by_the_glass"]
    pour = glass_cfg["pour_ml"]
    under_cost, under_bottle = [], []
    checked = 0
    for wine in wines:
        if not wine.btg or wine.glass_price is None:
            continue
        if wine.cost is not None and wine.cost > 0:
            checked += 1
            if wine.glass_price < wine.cost * glass_cfg["min_glass_price_to_bottle_cost"]:
                under_cost.append(f"{wine.label()}: glass {money(wine.glass_price, sym)}, "
                                  f"bottle cost {money(wine.cost, sym)}.")
        if wine.price is not None:
            pours = wine.size_ml() / pour
            revenue = wine.glass_price * pours
            if revenue < wine.price:
                under_bottle.append(
                    f"{wine.label()}: {pours:g} glasses of {pour} ml at {money(wine.glass_price, sym)} "
                    f"bring in {money(revenue, sym)}; the bottle sells for {money(wine.price, sym)}.")
    if under_cost:
        findings.append(Finding(
            FIX, "glass_pricing", f"{count(len(under_cost), 'glass price')} below the cost of the bottle",
            trimmed(under_cost, limit),
            "The first glass does not cover the bottle, so every open bottle depends on selling "
            "later pours before it fades. Any waste turns straight into loss.", 70))
    if under_bottle:
        findings.append(Finding(
            LOOK, "glass_pricing",
            f"{count(len(under_bottle), 'wine')} "
            + ("earns" if len(under_bottle) == 1 else "earn") + " less by the glass than by the bottle",
            trimmed(under_bottle, limit),
            "A table ordering glasses pays less than a table ordering the bottle, while the open "
            "bottle carries the waste risk. Usually the glass price is the one to raise.", 35))
    if checked and not under_cost:
        findings.append(Finding(FINE, "glass_pricing",
                                f"Glass prices cover the bottle cost for all {checked} costed "
                                "by-the-glass wines."))
    return findings, []


def check_ladder(wines, cfg, sym, limit):
    findings, missing = [], []
    ladder = cfg["price_ladder"]
    bottles = bottle_entries(wines)
    groups = type_groups(bottles, ladder["min_wines_per_group"])
    ok_groups = []
    for type_name, group in groups.items():
        prices = sorted({w.price for w in group})
        group_gaps = []
        for index in range(len(prices) - 1):
            low, high = prices[index], prices[index + 1]
            if high / low > ladder["max_step_ratio"] and high - low >= ladder["min_gap"]:
                group_gaps.append((index, low, high))
        if not group_gaps:
            ok_groups.append(f"{GROUP_NAMES[type_name]}: {money(prices[0], sym)} to "
                             f"{money(prices[-1], sym)} across {len(group)} bottles")
        for index, low, high in group_gaps:
            core = (index + 1) <= len(prices) * 2 / 3
            findings.append(Finding(
                FIX if core else LOOK, "ladder",
                f"Price gap in {'the ' + GROUP_NAMES[type_name] if type_name else 'the list'}: "
                f"nothing between {money(low, sym)} "
                f"and {money(high, sym)}",
                [],
                "Guests whose budget sits in this range must trade down or stretch up, and some "
                "will trade down. A bottle in the gap gives them a comfortable choice.",
                50 + high / low))
    if ok_groups:
        findings.append(Finding(FINE, "ladder", "Bottle prices step up without large gaps ("
                                + "; ".join(ok_groups) + ")."))
    untyped = [w for w in bottles if not w.type]
    if groups and "" not in groups and untyped:
        missing.append(f"Style (red, white, sparkling...) could not be read for {len(untyped)} "
                       "bottles; they were left out of the per-style price checks. Add a type "
                       "column or section headers.")
    return findings, missing


def check_second_cheapest(wines, cfg, sym, limit):
    findings, missing = [], []
    bottles = bottle_entries(wines)
    groups = type_groups(bottles, 3)
    costed_all = [w for w in bottles if valid_cost(w)]
    for type_name, group in groups.items():
        prices = sorted({w.price for w in group})
        if len(prices) < 2:
            continue
        second = sorted((w for w in group if w.price == prices[1]), key=lambda w: w.line_no)[0]
        where = (f"{second.label()} at {money(second.price, sym)} is the second-cheapest of "
                 f"{len(group)} {GROUP_NAMES[type_name]} (entry bottle {money(prices[0], sym)}).")
        noun = SINGULAR[type_name]
        if not valid_cost(second):
            findings.append(Finding(FINE, "second_cheapest", where))
            if costed_all:
                missing.append(f"Cost was not supplied for the second-cheapest {noun}, so its margin "
                               "could not be compared with the rest of the list.")
            continue
        group_costed = [w for w in group if valid_cost(w)]
        mine = margin_pct(second)
        multiple = second.price / second.cost
        where += f" Cost {money(second.cost, sym)}: {multiple:.2f}x, margin {mine:.0f}%."
        worst_list = len(costed_all) >= 3 and all(margin_pct(w) >= mine for w in costed_all)
        worst_group = len(group_costed) >= 3 and all(margin_pct(w) >= mine for w in group_costed)
        steepest = len(costed_all) >= 3 and all(w.price / w.cost <= multiple for w in costed_all)
        if worst_list or worst_group:
            scope = "on the whole list" if worst_list else f"among the {GROUP_NAMES[type_name]}"
            findings.append(Finding(
                FIX, "second_cheapest",
                f"The second-cheapest {noun} has the thinnest margin {scope}", [where],
                "The second-cheapest bottle is often a popular pick (check your own sales mix to "
                "confirm). If it is here, this thin margin repeats on a large share of bottles "
                "sold.", 65 if worst_list else 60))
        elif steepest:
            findings.append(Finding(
                LOOK, "second_cheapest",
                f"The second-cheapest {noun} carries the steepest markup on the list", [where],
                "Guests who trade up one step from the entry bottle get the least value on the "
                "list, and regulars notice. Worth checking it is a wine you are proud of at that "
                "price.", 38))
        else:
            findings.append(Finding(FINE, "second_cheapest",
                                    where + " Its margin is neither the thinnest nor the steepest."))
    return findings, missing


def check_btg(wines, cfg, sym, limit):
    findings = []
    glass_cfg = cfg["by_the_glass"]
    btg = [w for w in wines if w.btg]
    if not btg:
        findings.append(Finding(
            LOOK, "btg", "Nothing is offered by the glass", [],
            "Guests who want a single glass, or a different wine with each course, have no "
            "option, and those sales are lost.", 45))
        return findings, []
    types = {w.type for w in btg if w.type}
    missing_core = [t for t in glass_cfg["expected_types"] if t not in types]
    still_core = [t for t in missing_core if t in ("white", "red")]
    if still_core:
        findings.append(Finding(
            FIX, "btg", "No " + " or ".join(GROUP_NAMES[t] for t in still_core) + " by the glass",
            [], "A guest who wants one glass of red or white is the most common glass order; "
            "without one, that order is lost or pushed to a bottle.", 55))
    other_missing = [t for t in missing_core if t not in still_core]
    if other_missing:
        findings.append(Finding(
            LOOK, "btg", "No " + " or ".join(GROUP_NAMES[t] for t in other_missing)
            + " by the glass", [],
            "A glass of sparkling is a common way to start a meal; without one the opening "
            "order often goes to something lower value.", 33))
    if len(btg) < glass_cfg["min_count"]:
        findings.append(Finding(
            LOOK, "btg", f"Only {count(len(btg), 'wine')} by the glass (your target is "
            f"{glass_cfg['min_count']})", [],
            "A narrow glass list limits pairing by the course and gives guests little to choose "
            "from.", 32))
    glass_prices = sorted(w.glass_price for w in btg if w.glass_price is not None)
    if len(glass_prices) >= 4 and glass_prices[-1] / glass_prices[0] < glass_cfg["min_price_spread"]:
        findings.append(Finding(
            LOOK, "btg", f"Glass prices sit in a narrow band ({money(glass_prices[0], sym)} to "
            f"{money(glass_prices[-1], sym)})", [],
            "There is no clear step-up glass for guests who would happily spend a little more.", 31))
    bottle_keys = {(fold(w.producer), fold(w.name)) for w in wines if not w.btg and w.price}
    also_bottle = sum(1 for w in btg if w.price is not None
                      or (fold(w.producer), fold(w.name)) in bottle_keys)
    summary = f"{count(len(btg), 'wine')} by the glass"
    if types:
        order = [t for t in ("sparkling", "white", "orange", "rose", "red", "sweet", "fortified")
                 if t in types]
        summary += " (" + ", ".join(GROUP_NAMES[t] for t in order) + ")"
    if glass_prices:
        summary += f", glass prices {money(glass_prices[0], sym)} to {money(glass_prices[-1], sym)}"
    summary += f"; {also_bottle} of them also sold by the bottle."
    nice_missing = [t for t in glass_cfg["nice_to_have_types"] if t not in types]
    if nice_missing:
        summary += (" Optional extras not offered by the glass: "
                    + ", ".join(GROUP_NAMES[t] for t in nice_missing) + ".")
    findings.append(Finding(FINE, "btg", summary))
    return findings, []


def wine_styles(wine: Wine, rules: dict) -> set[str]:
    text = wine.search_text()
    tags = {style for style, words in rules["wine_styles"].items()
            if any(has_word(text, fold(word)) for word in words)}
    if wine.type in COMPATIBLE_STYLES:
        tags &= COMPATIBLE_STYLES[wine.type]
    if not tags:
        tags = set(rules["type_fallback_styles"].get(wine.type, []))
    return tags


def parse_menu(text: str) -> list[str]:
    dishes = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.endswith(":"):
            continue
        letters = [c for c in line if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            continue
        line = re.sub(r"\s*[$€£]?\s?\d{1,4}(?:[.,]\d{2})?\s*$", "", line).strip()
        if line:
            dishes.append(line)
    return dishes


def dish_name(line: str) -> str:
    return re.split(r",|\s[|·]\s|\s-\s|\(", line, maxsplit=1)[0].strip()


def check_menu(wines, menu_text, rules, sym, limit):
    findings, missing = [], []
    if menu_text is None:
        missing.append("No menu was supplied, so pairing coverage was not checked. "
                       "Pass one with --menu.")
        return findings, missing
    dishes = parse_menu(menu_text)
    styles = {id(w): wine_styles(w, rules) for w in wines}
    unknown = [w for w in wines if styles[id(w)] <= {"white_unknown", "red_unknown"}]
    no_match, bottle_only, unclassified = [], [], []
    covered = 0
    for dish in dishes:
        folded = fold(dish)
        cats = [c for c in rules["dish_categories"]
                if any(has_word(folded, fold(k)) for k in c["keywords"])]
        if not cats:
            unclassified.append(dish_name(dish))
            continue
        allowed = set(cats[0]["styles"])
        for cat in cats[1:]:
            allowed &= set(cat["styles"])
        if not allowed:
            allowed = set().union(*(set(c["styles"]) for c in cats))
        matches = [w for w in wines if styles[id(w)] & allowed]
        by_glass = [w for w in matches if w.btg]
        wanted = join_or([STYLE_NAMES[s] for s in sorted(allowed)])
        cat_labels = " and ".join(c["label"] for c in cats)
        if not matches:
            no_match.append(f"{dish_name(dish)} ({cat_labels}): nothing {wanted} on the list.")
        elif not by_glass:
            bottle_only.append(f"{dish_name(dish)} ({cat_labels}): {count(len(matches), 'match', 'matches')} by "
                               f"the bottle, none by the glass.")
        else:
            covered += 1
    if no_match:
        findings.append(Finding(
            FIX, "menu", f"{count(len(no_match), 'dish', 'dishes')} with no sensible pairing on the list",
            trimmed(no_match, limit),
            "Guests ordering these dishes either drink something that fights the food or skip "
            "wine, and staff have nothing confident to suggest.", 60))
    if bottle_only:
        findings.append(Finding(
            LOOK, "menu", f"{count(len(bottle_only), 'dish', 'dishes')} "
            + ("pairs" if len(bottle_only) == 1 else "pair") + " by the bottle only",
            trimmed(bottle_only, limit),
            "A guest who wants one glass with this dish has no good match.", 34))
    if covered:
        findings.append(Finding(FINE, "menu",
                                f"{covered} of {len(dishes)} dishes have at least one sensible "
                                "match by the glass."))
    if unclassified:
        missing.append(f"Could not classify {count(len(unclassified), 'dish', 'dishes')}, so check "
                       + ("it" if len(unclassified) == 1 else "them") + " by hand: "
                       + "; ".join(unclassified) + ".")
    if unknown:
        missing.append(f"Style could not be read for {count(len(unknown), 'wine')} (no grape or region "
                       "the rules recognise), so menu coverage may be understated: "
                       + "; ".join(w.label() for w in unknown[:limit])
                       + ("; ..." if len(unknown) > limit else "") + ".")
    return findings, missing


def check_duplicates(wines, cfg, sym, limit):
    findings = []
    seen: dict[tuple, list[Wine]] = {}
    for wine in wines:
        key = (re.sub(r"\W+", " ", fold(wine.producer)).strip(),
               re.sub(r"\W+", " ", fold(wine.name)).strip(), wine.vintage, wine.size_ml(), wine.btg)
        seen.setdefault(key, []).append(wine)
    clash, same = [], []
    for group in seen.values():
        if len(group) < 2:
            continue
        prices = sorted({(w.price, w.glass_price) for w in group}, key=str)
        lines_ref = ", ".join(f"line {w.line_no}" for w in group)
        if len(prices) > 1:
            shown = "; ".join(f"line {w.line_no}: " + (money(w.price, sym) if w.price else "no price")
                              for w in group)
            clash.append(f"{group[0].label()}: {shown}.")
        else:
            same.append(f"{group[0].label()} ({lines_ref}).")
    if clash:
        findings.append(Finding(
            FIX, "duplicates", f"{count(len(clash), 'wine')} listed twice at different prices", clash,
            "Guests and staff see two prices for one wine, and a guest who has seen the lower "
            "price will expect it.", 90))
    if same:
        findings.append(Finding(LOOK, "duplicates", f"{count(len(same), 'wine')} listed twice", same,
                                "Takes space a different wine could use.", 30))
    near = []
    keys = [(w, re.sub(r"[^a-z0-9]+", " ", fold(f"{w.producer} {w.name}")).strip()) for w in wines]
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, ka = keys[i]
            b, kb = keys[j]
            if ka == kb or a.vintage != b.vintage or a.btg != b.btg or a.size_ml() != b.size_ml():
                continue
            if SequenceMatcher(None, ka, kb).ratio() >= 0.88:
                near.append(f"line {a.line_no} '{a.label()}' and line {b.line_no} '{b.label()}'.")
    if near:
        findings.append(Finding(LOOK, "duplicates",
                                f"{count(len(near), 'possible near-duplicate')} or spelling variant"
                                + ("" if len(near) == 1 else "s"),
                                trimmed(near, limit),
                                "Usually a typo, which makes the list look careless and can "
                                "confuse stock counts.", 29))
    if not clash and not same and not near:
        findings.append(Finding(FINE, "duplicates", "No duplicates or near-duplicates found."))
    return findings, []


def check_vintage_format(wines, cfg, sym, limit, year):
    findings, missing = [], []
    future = [w for w in wines if w.vintage.isdigit() and int(w.vintage) > year]
    if future:
        findings.append(Finding(
            FIX, "vintage", f"{count(len(future), 'vintage')} later than {year}",
            [f"line {w.line_no}: {w.label()}." for w in future],
            "Almost certainly a typing error; guests and staff lose trust in the list.", 85))
    still = [w for w in wines if w.type not in ("sparkling", "fortified")]
    no_vintage = [w for w in still if not w.vintage]
    nv_still = [w for w in still if w.vintage == "NV" and w.type in ("red", "white", "rose")]
    odd_lines = ([f"line {w.line_no}: {w.label()}: no vintage shown." for w in no_vintage]
                 + [f"line {w.line_no}: {w.label()}: still wine listed as NV." for w in nv_still])
    if odd_lines:
        findings.append(Finding(
            LOOK, "vintage", f"{count(len(odd_lines), 'still wine')} without a clear vintage",
            trimmed(odd_lines, limit),
            "Guests and staff can't tell which vintage they will get, and a vintage change can "
            "slip through unnoticed.", 36))
    notations = {}
    for wine in wines:
        if wine.format_raw:
            notations.setdefault(format_notation(wine.format_raw), wine.format_raw)
    if len(notations) > 1:
        findings.append(Finding(
            LOOK, "format", f"Formats are written {len(notations)} different ways ("
            + ", ".join(sorted(notations.values())) + ")", [],
            "Small, but a consistent list reads as a careful one.", 20))
    formats_cfg = cfg["formats"]
    by_wine: dict[tuple, dict[int, Wine]] = {}
    for wine in wines:
        if wine.price is None:
            continue
        key = (fold(wine.producer), fold(wine.name), wine.vintage)
        by_wine.setdefault(key, {})[wine.size_ml()] = wine
    magnum_lines, half_lines = [], []
    for sizes in by_wine.values():
        bottle = sizes.get(750)
        if not bottle:
            continue
        magnum = sizes.get(1500)
        if magnum and magnum.price < bottle.price * formats_cfg["magnum_min_price_multiple"]:
            target = bottle.price * formats_cfg["magnum_min_price_multiple"]
            magnum_lines.append(
                f"{magnum.label()}: {money(magnum.price, sym)} against {money(bottle.price, sym)} "
                f"for the bottle. At {formats_cfg['magnum_min_price_multiple']:g}x the bottle it "
                f"would be {money(target, sym)}, {money(target - magnum.price, sym)} more.")
        half = sizes.get(375)
        if half and half.price >= bottle.price:
            half_lines.append(f"{half.label()}: {money(half.price, sym)}, bottle "
                              f"{money(bottle.price, sym)}.")
    if half_lines:
        findings.append(Finding(FIX, "format", "Half bottle priced at or above the full bottle",
                                half_lines, "Almost certainly an error, and guests will spot it.", 75))
    if magnum_lines:
        findings.append(Finding(
            LOOK, "format", "Magnum priced under your multiple of the bottle price", magnum_lines,
            "A magnum costs more to buy and to hold than two bottles; underpricing it gives away "
            "margin on a special-occasion sale.", 37))
    if not future and not odd_lines:
        findings.append(Finding(FINE, "vintage", "Every still wine shows a plausible vintage."))
    no_format = [w for w in wines if not w.format_raw]
    if no_format and len(no_format) < len(wines):
        missing.append(f"Format not shown for {count(len(no_format), 'wine')}; "
                       f"{formats_cfg['assumed_ml_when_missing']} ml was assumed.")
    elif no_format:
        missing.append(f"No formats were given; every wine was treated as "
                       f"{formats_cfg['assumed_ml_when_missing']} ml.")
    return findings, missing


def data_impact(lines: list[str]) -> str:
    parts = []
    if any("no menu price" in line for line in lines):
        parts.append("A wine with no price slows service and invites a price made up at the table.")
    if any("cost is equal" in line for line in lines):
        parts.append("A price at or below cost loses money on every sale.")
    if any("glass price is equal" in line for line in lines):
        parts.append("A glass priced at or above its bottle is almost certainly a typing error.")
    return " ".join(parts)


def check_data(wine_list: WineList, cfg, sym, limit):
    findings, missing = [], []
    serious, minor = [], []
    for wine in wine_list.wines:
        for problem in wine.problems:
            line = f"line {wine.line_no}: {wine.label()}: {problem}."
            if problem in ("no menu price", "cost is equal to or above the menu price",
                           "glass price is equal to or above the bottle price"):
                serious.append(line)
            else:
                minor.append(line)
    if serious:
        findings.append(Finding(
            FIX, "data", f"{count(len(serious), 'data problem')} a guest or the till would hit",
            trimmed(serious, limit),
            data_impact(serious), 100))
    if minor or wine_list.skipped_lines:
        lines = minor + [f"line {n}: could not read '{text[:60]}'." for n, text in
                         wine_list.skipped_lines]
        findings.append(Finding(LOOK, "data", f"{count(len(lines), 'smaller data problem')}",
                                trimmed(lines, limit), "Worth tidying before the next print.", 25))
    if not serious and not minor and not wine_list.skipped_lines:
        findings.append(Finding(FINE, "data", "Every line was read with a name and a price."))
    if wine_list.unused_columns:
        missing.append("Columns not used by the audit: " + ", ".join(wine_list.unused_columns) + ".")
    return findings, missing


# Report ---------------------------------------------------------------------

def audit(wine_list: WineList, menu_text: str | None, cfg: dict, rules: dict, year: int,
          title: str, limit: int) -> Report:
    sym = cfg.get("currency_symbol", "$")
    wines = wine_list.wines
    findings, missing = check_data(wine_list, cfg, sym, limit)
    for check in (check_markups, check_glass_pricing, check_ladder, check_second_cheapest,
                  check_btg, check_duplicates):
        f, m = check(wines, cfg, sym, limit)
        findings += f
        missing += m
    f, m = check_vintage_format(wines, cfg, sym, limit, year)
    findings += f
    missing += m
    f, m = check_menu(wines, menu_text, rules, sym, limit)
    findings += f
    missing += m
    bottles = sum(1 for w in wines if w.price is not None)
    btg = sum(1 for w in wines if w.btg)
    summary = f"Read {len(wines)} wines ({bottles} with a bottle price, {btg} by the glass)."
    if menu_text is not None:
        summary += f" Menu: {len(parse_menu(menu_text))} dishes."
    return Report(title, summary, findings, missing)


def render(report: Report) -> str:
    out = [f"# Wine list audit: {report.title}", "", report.summary,
           "Price bands come from references/pricing-defaults.json. They are starting "
           "assumptions to be confirmed, not industry facts.", ""]
    out.append("## Fix first")
    out.append("")
    fixes = report.by_level(FIX)
    if not fixes:
        out += ["Nothing urgent found.", ""]
    for number, finding in enumerate(fixes, 1):
        out.append(f"{number}. **{finding.title}.**")
        out += [f"   - {line}" for line in finding.lines]
        out.append(f"   - Likely money impact: {finding.impact}")
        out.append("")
    out.append("## Worth a look")
    out.append("")
    looks = report.by_level(LOOK)
    if not looks:
        out += ["Nothing else stood out.", ""]
    for number, finding in enumerate(looks, 1):
        out.append(f"{number}. **{finding.title}.**")
        out += [f"   - {line}" for line in finding.lines]
        if finding.impact:
            out.append(f"   - Why it matters: {finding.impact}")
        out.append("")
    out.append("## Fine as is")
    out.append("")
    out += [f"- {f.title}" for f in report.by_level(FINE)] or ["- Nothing to report."]
    out.append("")
    if report.missing:
        out.append("## What's missing")
        out.append("")
        out += [f"- {line}" for line in report.missing]
        out.append("")
    out.append(CLOSING_LINE)
    return "\n".join(out) + "\n"


def to_json(report: Report) -> str:
    data = {
        "title": report.title,
        "summary": report.summary,
        "fix_first": [asdict(f) for f in report.by_level(FIX)],
        "worth_a_look": [asdict(f) for f in report.by_level(LOOK)],
        "fine_as_is": [asdict(f) for f in report.by_level(FINE)],
        "missing": report.missing,
        "closing": CLOSING_LINE,
    }
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def run(list_text: str, menu_text: str | None = None, config_path: Path | None = None,
        year: int | None = None, title: str = "wine list", as_json: bool = False,
        show_all: bool = False) -> str:
    cfg = load_json(config_path or REFERENCES / "pricing-defaults.json")
    rules = load_json(REFERENCES / "pairing-rules.json")
    year = year or datetime.date.today().year
    limit = 10_000 if show_all else cfg.get("report", {}).get("max_lines_per_finding", 5)
    wine_list = parse_wine_list(list_text, year)
    report = audit(wine_list, menu_text, cfg, rules, year, title, limit)
    return to_json(report) if as_json else render(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a wine list and print a ranked report.")
    parser.add_argument("list", help="wine list file (CSV, TSV or text), or - for stdin")
    parser.add_argument("--menu", help="menu file (plain text, one dish per line)")
    parser.add_argument("--config", help="pricing settings JSON (default: references/pricing-defaults.json)")
    parser.add_argument("--year", type=int, help="current year for vintage checks (default: this year)")
    parser.add_argument("--title", help="name to show at the top of the report")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    parser.add_argument("--all", action="store_true", help="show every line in each finding")
    args = parser.parse_args(argv)
    if args.list == "-":
        list_text = sys.stdin.read()
        title = args.title or "pasted wine list"
    else:
        list_text = Path(args.list).read_text(encoding="utf-8-sig")
        title = args.title or Path(args.list).name
    menu_text = Path(args.menu).read_text(encoding="utf-8-sig") if args.menu else None
    sys.stdout.write(run(list_text, menu_text, Path(args.config) if args.config else None,
                         args.year, title, args.json, args.all))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
