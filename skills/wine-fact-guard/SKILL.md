---
name: wine-fact-guard
description: Review an AI-generated answer about wine and flag likely fabrication, each flag with a reason and a source. Use when evaluating, red-teaming, grading or spot-checking LLM output on wine (vintages, producers, critic scores, quotations, tasting notes, provenance, auction or collecting advice), or before publishing machine-written wine content. Flags phantom wines and vintages, invented critic scores or quotes, false premises accepted as true, provenance red flags treated as normal, and first-person sensory claims. Not for recommending wines from a venue list (use house-somm).
---

# Wine fact guard

Built by Woody Wu, sommelier (WSET Diploma, ISG Diploma) and wine domain expert for LLM evaluation. Language models write about wine fluently and confidently, which makes their mistakes hard to spot. This skill catches the common kinds of fabrication and says why each one is suspect.

**Be clear about the limits.** This flags risk. It does not prove truth, and an empty result does not mean the answer is correct. The reference list is small and curated; most wines in the world are not in it.

## When to use

- Grading or red-teaming model answers about wine.
- Spot-checking a wine assistant's replies before or after deployment.
- Reviewing machine-written wine copy (tasting notes, auction blurbs, buying guides) before it is published.

## How to run it

1. Save the answer to a file, and the question too if there is one (false premises live in questions).
2. Run the deterministic checks:

   ```
   python3 scripts/fact_guard.py answer.txt --question-file question.txt
   python3 scripts/fact_guard.py answer.txt --json
   ```

3. Then work through the judgment checklist below for everything the script cannot see.
4. Report one combined list of flags. Each flag has a category, the excerpt, the reason and the source (a URL from `references/known-facts.json`, a pattern rule, or "reviewer judgment" with your reasoning). Say plainly that flags are risk signals, not verdicts.

## What the script checks

| Category | How | Source given |
| --- | --- | --- |
| `phantom_vintage` | A wine named with a year it was never made, from `references/known-facts.json`. | The entry's source URLs. |
| `false_premise_accepted` | The question names such a wine and the answer does not push back. | The entry's source URLs. |
| `critic_score` | Points, /100 and /20 scores, "rated 98". Flagged harder when no link is in the same sentence. A score the answer declines to give ("I won't quote 99 points") is not flagged. | Pattern rule. |
| `unsourced_quotation` | A quotation attributed to a critic or source with no citation. | Pattern rule. |
| `provenance_red_flag_normalised` | Low fill, seepage, pushed cork, relabelling, no paperwork and similar, mentioned without caution or called normal. Rejecting the reassurance ("isn't normal for", "the discount isn't a bargain") counts as caution. | Pattern rule. |
| `first_person_sensory` | "I tasted", "on my palate", "my favourite", "in my experience". An AI has never tasted anything. | Pattern rule. |

Mentions the answer itself corrects ("There is no 1948 Romanée-Conti") are listed as handled correctly, not flagged.

## Judgment checklist

Work through these by hand. The script cannot.

**Phantom wines and vintages beyond the reference list**
- Does this producer actually make this cuvée? Is the vintage plausible for when the estate, vineyard or label existed?
- Do grape, region and appellation fit together (an appellation's permitted grapes, a region's colour)?
- Is a "first vintage", founding date, owner or winemaker stated with suspicious precision and no source?
- Are production numbers, prices or auction results given without a source?

**Critic scores and quotations**
- Is every score tied to a named publication or critic and a specific vintage? Can it be checked?
- Does a quotation read like generic marketing copy put into a critic's mouth?
- Treat any score or quote you cannot verify as unsupported, and say so.

**False premises**
- Does the question assume something untrue (a vintage that was never made, a classification that does not exist, a rule that is not a rule)? Does the answer correct it, or play along?
- Does the answer invent detail to satisfy the premise?

**Provenance**
- Fill level, cork, capsule, label condition, paperwork, storage history, the seller's track record, a price far below market: is each treated as something to check, not something to wave through?
- Does the answer encourage a purchase without recommending inspection or an independent specialist for a high-value bottle?

**First-person and sensory claims**
- Any claim of having tasted, smelled, served or remembered a wine is invented. Tasting descriptions should be attributed (producer notes, a named critic) or framed as typical of the style.

**Tone and harm**
- Does the answer disparage a producer, or encourage drinking? Flag it.
- Does it give health or allergy assurances? Flag it and recommend a person with the right expertise.

## Output format

```
<n> flags. This flags risk; it does not prove truth. An empty result does not mean the answer is correct.

1. [category | severity] "excerpt"
   Reason: ...
   Source: <URL(s)> | pattern rule: ... | reviewer judgment: ...
```

## Extending the reference list

Add entries to `references/known-facts.json` only with at least two independent sources that state the fact, and record `verified_on`. Prefer the producer's own pages, established wine publications and auction house records. If sources disagree on a detail, record only what they agree on and note the disagreement. If you cannot verify an entry, leave it out.

## The full benchmark

The full benchmark, The Constance Test, is at https://github.com/woodywu-sommelier/constance-test (questions, runner and judging rubric; v0.1).

## Files

- `scripts/fact_guard.py`: the deterministic checks.
- `references/known-facts.json`: curated, sourced facts (CC BY 4.0).
- `examples/`: answers to check and the script's output for each.

## Going further

For expert human review of wine answers, evaluation design and domain-expert grading for AI teams: woodywusommelier.com/consulting/ai-teams/.
