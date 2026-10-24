---
license: cc-by-4.0
language:
  - en
pretty_name: Hospitality Skills Examples
size_categories:
  - n<1K
tags:
  - wine
  - sommelier
  - hospitality
  - restaurants
  - llm-evaluation
  - hallucination
  - agent-skills
configs:
  - config_name: known_facts
    data_files: known-facts/known-facts.jsonl
  - config_name: juniper_table_list
    data_files: wine-lists/juniper-table-list.csv
  - config_name: copper_fig_list
    data_files: wine-lists/copper-fig-list.csv
---

# Hospitality Skills Examples

Example data and reference facts from [Hospitality Skills by Woody Wu](https://github.com/woodywu-sommelier/hospitality-skills), an open-source pack of Agent Skills for restaurant, hotel and sommelier work. The code lives on GitHub; this dataset holds the data so it can be browsed, downloaded and cited on its own.

## Files

| File | What it is |
| --- | --- |
| `known-facts/known-facts.json` | Curated, sourced historical facts: wine vintages that were never made, and first vintages. Each entry has the fact, match rules, at least two source URLs and a verification date. Used by the `wine-fact-guard` skill to flag phantom vintages in AI answers. |
| `known-facts/known-facts.jsonl` | The same entries, one per line, for the dataset viewer. |
| `wine-lists/juniper-table-list.csv` | A fictional restaurant wine list with costs, menu prices and by-the-glass prices, with planted issues for the `wine-list-audit` skill. |
| `wine-lists/juniper-table-menu.txt` | The fictional menu that goes with it. |
| `wine-lists/juniper-table-expected-report.md` | The audit report the skill produces for that list and menu. |
| `wine-lists/bistro-lanterne-list.txt` | A fictional list as pasted plain text, with no costs. |
| `wine-lists/bistro-lanterne-expected-report.md` | The audit report for it, including what was skipped for lack of data. |
| `wine-lists/copper-fig-list.csv` | A fictional list used by the `house-somm` skill to check that an assistant names only wines on the list. |

## Important notes

- **Every venue and producer in the wine lists is fictional.** Regions and grapes are real so the style checks work. Prices and costs are invented and say nothing about any real wine.
- **Real producers appear only in the known facts**, and only as sourced historical facts.
- **The known facts flag risk; they do not prove truth.** The list is small and curated. A wine missing from it is not thereby real or fake.
- Entries were checked against their sources on the date in `verified_on`. Open the links before relying on an entry.

## Licence and citation

CC BY 4.0. Credit: "Hospitality Skills by Woody Wu (woodywusommelier.com), CC BY 4.0". See [CITATION.cff](https://github.com/woodywu-sommelier/hospitality-skills/blob/main/CITATION.cff) in the GitHub repository.

## About the author

Woody Wu is a sommelier (WSET Diploma, ISG Diploma), hospitality operator and AI builder: [woodywusommelier.com](https://woodywusommelier.com). For wine and hospitality domain expertise in LLM evaluation, see [woodywusommelier.com/consulting/ai-teams/](https://woodywusommelier.com/consulting/ai-teams/).
