# Hospitality Skills by Woody Wu

Agent Skills for real restaurant, hotel and sommelier work, written by a working sommelier. Three skills, each useful on day one, each with plain Python 3.11 scripts that use the standard library only: nothing to install, no API keys, no data leaves your machine.

| Skill | Who it's for | What it does |
| --- | --- | --- |
| [`wine-list-audit`](skills/wine-list-audit/) | Restaurant owners, GMs, beverage directors | Reads your wine list (CSV or pasted text) and an optional menu, and returns a short ranked report: **Fix first**, **Worth a look**, **Fine as is**. Checks markups against your own targets, price ladder gaps, the second-cheapest bottle, the by-the-glass range, dishes with no sensible pairing, duplicates, vintage and format oddities, and data problems. |
| [`house-somm`](skills/house-somm/) | Restaurants, and AI teams building wine assistants | Makes an assistant recommend only wines on your list, quoting the exact list line (name, vintage, price), matched to the dish, the budget and the guest. Includes a reference prompt and `check_reply.py`, which flags any named wine that is not on the list, a wrong vintage or price, first-person tasting claims, and a missing hand-off to a person. |
| [`wine-fact-guard`](skills/wine-fact-guard/) | AI teams evaluating wine answers | Reviews an AI-generated wine answer and flags likely fabrication: phantom wines and vintages, invented critic scores or quotations, false premises accepted as true, provenance red flags treated as normal, and first-person sensory claims. Every flag comes with a reason and a source. |

## Quick start (60 seconds)

You need Python 3.11 or newer. Nothing else.

```
git clone https://github.com/woodywu-sommelier/hospitality-skills
cd hospitality-skills

# Audit a fictional wine list against its menu
python3 skills/wine-list-audit/scripts/audit_list.py \
  skills/wine-list-audit/examples/juniper-table-list.csv \
  --menu skills/wine-list-audit/examples/juniper-table-menu.txt

# Check an assistant's reply against a fictional list
python3 skills/house-somm/scripts/check_reply.py \
  --list skills/house-somm/examples/copper-fig-list.csv \
  --reply skills/house-somm/examples/reply-bad-invented.md

# Flag fabrication in an AI wine answer
python3 skills/wine-fact-guard/scripts/fact_guard.py \
  skills/wine-fact-guard/examples/answer-auction-lots.md
```

Then swap in your own files. Your wine list can be a spreadsheet export or text pasted into a file (or piped in with `-`).

### Use them as Agent Skills

- **Claude Code**: `/plugin marketplace add woodywu-sommelier/hospitality-skills`, then `/plugin install hospitality-skills@hospitality-skills`. Or copy any folder under `skills/` into `~/.claude/skills/`.
- **Claude apps with custom skills**: zip a single skill folder (for example `skills/wine-list-audit/`) and upload it as a custom skill.
- **Any other agent**: each `SKILL.md` is plain Markdown with YAML front matter (`name`, `description`). Point your agent at the folder; the scripts run anywhere Python does.

## For owners and managers

Hand your list to `wine-list-audit` and you get the first pass a sommelier would make, ranked by what costs you money. A shortened example from the fictional list in `skills/wine-list-audit/examples/`:

```
## Fix first

1. **1 wine listed twice at different prices.**
   - Bodega Inventada, Reserva 2018: line 13: $74; line 19: $78.
   - Likely money impact: Guests and staff see two prices for one wine, and a guest who has seen the lower price will expect it.

2. **2 bottles priced below your markup band.**
   - Paper Moon Vineyards, Pinot Noir 2021: cost $26, price $64, 2.46x (your band 2.6x to 3.5x). At 2.6x the price would be $67.60, $3.60 more per bottle sold.
```

What it will never do: invent costs, sales or prices. If your list has no costs, the report says markups were not checked and why. The markup bands are starting assumptions in a settings file for you to change, not industry rules.

`house-somm` is the same discipline on the floor: an assistant that only sells what is in your cellar, respects a guest's budget without making them say a number, offers a glass when there is one, and calls a person for allergies, faulty bottles and very high-value bottles.

## For AI engineers

- **Guardrail**: run `check_reply.py` on every assistant reply. It exits `1` on any flag and prints JSON with `--json`, so it drops into a pipeline or CI. Block or regenerate on `not_on_list`, `vintage_mismatch`, `price_mismatch` and `sensory_claim`.
- **Evaluation**: `fact_guard.py` gives deterministic flags (sourced known facts, score and quotation patterns, provenance and sensory patterns), and `SKILL.md` gives the model a judgment checklist for everything else. Use both: the script is high precision on a narrow set; the checklist covers the long tail.
- **Reference data**: `skills/wine-fact-guard/references/known-facts.json` lists vintages that were never made and first vintages, each with source URLs and a verification date. Entries are added only with two independent sources.
- **Honest limits**: the fact guard flags risk. It does not prove truth, and an empty result does not mean an answer is correct. The full benchmark, The Constance Test, is coming.

## What's in the box

```
skills/
  wine-list-audit/   SKILL.md, scripts/audit_list.py, references/ (pricing defaults, pairing rules), examples/
  house-somm/        SKILL.md, scripts/check_reply.py, references/ (reference prompt, house settings), examples/
  wine-fact-guard/   SKILL.md, scripts/fact_guard.py, references/known-facts.json, examples/
tests/               standard library unittest suite
huggingface/         dataset card and build script for the example data on Hugging Face
```

Run the tests with:

```
python3 -m unittest discover -s tests -v
```

The example wine lists and the known-facts reference are also published as a dataset on Hugging Face: [woodywu-sommelier/hospitality-skills-examples](https://huggingface.co/datasets/woodywu-sommelier/hospitality-skills-examples).

## Who built this

**Woody Wu** is a sommelier with both the WSET Diploma and the ISG Diploma, a hospitality operator and an AI builder. He works where restaurant and hotel service meets AI: building assistants that venues can trust, and helping AI teams measure whether their models get wine right.

- [woodywusommelier.com](https://woodywusommelier.com)
- **Service Audit** for restaurants and hotels, from $3,500 CAD: [woodywusommelier.com/consulting/](https://woodywusommelier.com/consulting/)
- **The House Somm**, an AI sommelier that answers only from a venue's own list. Live demo: [concierge.woodywusommelier.com](https://concierge.woodywusommelier.com)
- **For AI Teams**: wine and hospitality domain expertise for LLM evaluation: [woodywusommelier.com/consulting/ai-teams/](https://woodywusommelier.com/consulting/ai-teams/)

The House Somm (concierge.woodywusommelier.com) is the hosted version of the `house-somm` skill, deployed on a venue's own list and menu.

## Ground rules for contributions

- Example lists use fictional producers only. Real producers appear only in sourced historical facts.
- New entries in `known-facts.json` need at least two independent sources and a `verified_on` date.
- Never disparage a producer. Nothing in this repository should encourage drinking.
- Scripts stay standard library only.

## Licence

Code: [MIT](LICENSE). Example and reference data: [CC BY 4.0](LICENSE-DATA). If you use this work, please cite it ([CITATION.cff](CITATION.cff)).
