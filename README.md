---
title: Did your AI invent a wine?
emoji: 🍷
colorFrom: red
colorTo: gray
sdk: gradio
sdk_version: 6.30.0
python_version: "3.11"
app_file: app.py
pinned: false
license: mit
short_description: Paste a chatbot's wine answer; see what it invented
tags:
  - wine
  - hallucination
  - llm-evaluation
---

# Did your AI invent a wine?

Paste a chatbot's answer about a wine. This page checks it against a sourced list of wines that were never made, and flags invented scores and tasting claims. Built by sommelier Woody Wu ([woodywusommelier.com](https://woodywusommelier.com)).

Nothing you paste is stored. The page makes no model or API calls: the check is a deterministic Python script that runs on the Space itself.

## What it checks

- **Wines that were never made**: a wine named with a vintage from the sourced list in `vendor/wine-fact-guard/references/known-facts.json`, such as a 2001 Dom Pérignon or a 1947 Romanée-Conti. Each entry has at least two sources and a `verified_on` date, and each flag links to them.
- **False premises**: if you add the question, an answer that plays along with a wine that was never made.
- **Critic scores with no source**: "96 points", "98/100" and similar, with no link.
- **Quotations with no source**: a quote attributed to a critic, with no citation.
- **First-person tasting claims**: "I tasted", "on my palate". A chatbot has never tasted anything.
- **Bottle warning signs treated as normal**: low fill, a pushed cork, no paperwork, called normal or mentioned without caution.

An answer that correctly says a wine does not exist is listed as handled correctly, not flagged.

## What it can't check

- Wines and vintages that are not on the list. The list is short on purpose: every entry is sourced.
- Whether a score, quote or tasting note is accurate. It only notices that one is there without a source.
- Prices, producers, grapes, regions and anything else that needs judgment.

This flags risk. It does not prove an answer right or wrong, and an empty result does not mean the answer is correct.

## Source

The checker is vendored, unchanged, from [woodywu-sommelier/hospitality-skills](https://github.com/woodywu-sommelier/hospitality-skills) at commit [`de644a6e2dd5ffa3460551c654012cd5c1eb6395`](https://github.com/woodywu-sommelier/hospitality-skills/tree/de644a6e2dd5ffa3460551c654012cd5c1eb6395):

- `vendor/wine-fact-guard/scripts/fact_guard.py` from `skills/wine-fact-guard/scripts/fact_guard.py`
- `vendor/wine-fact-guard/references/known-facts.json` from `skills/wine-fact-guard/references/known-facts.json`

To update, copy both files from a newer commit, run the tests, and change the commit above.

The example answers on the page are fabrications written for this page, not quotes from any model.

## Add a fact

Facts are added in hospitality-skills, not here. Open a pull request that adds an entry to `skills/wine-fact-guard/references/known-facts.json` with at least two independent sources that state the fact, from two different sites, and a `verified_on` date. Prefer the producer's own pages, established wine publications and auction house records. If sources disagree on a detail, record only what they agree on. Then update the vendored copy here.

## Run it locally

```
pip install gradio==6.30.0
python app.py
python -m unittest discover -s tests
```

## Licence

- Code: MIT (see `LICENSE`).
- Facts in `known-facts.json`: CC BY 4.0 (see `LICENSE-DATA`).

## Links

- Code: [github.com/woodywu-sommelier/hospitality-skills](https://github.com/woodywu-sommelier/hospitality-skills)
- Benchmark: [The Constance Test](https://woodywusommelier.com/constance-test/) ([code](https://github.com/woodywu-sommelier/constance-test))
- Expert review for AI teams: [woodywusommelier.com/consulting/ai-teams/](https://woodywusommelier.com/consulting/ai-teams/)
