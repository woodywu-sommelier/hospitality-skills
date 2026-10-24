# Examples

Answers to check, as an AI wine assistant might write them, with the script's output for each. Answers about real wines use only the sourced facts in `references/known-facts.json`. The scores, quotation, tasting claims and sale details are attached to a fictional wine (Château Nullepart is invented) so that no real producer or critic is misquoted.

| File | What it shows |
| --- | --- |
| `answer-phantom.md` + `q-phantom.txt` | An answer that accepts a vintage that was never made (false premise accepted, phantom vintage). |
| `answer-correct.md` | An answer that corrects the same premise. No flags. |
| `answer-auction-lots.md` | Four phantom vintages from the reference list, mixed with real ones that must not be flagged. |
| `answer-fictional-scores.md` | Uncited critic score, an unsourced quotation, first-person tasting claims and a provenance warning sign presented as normal. |
| `*.expected.txt` | The script's output for each answer. |

Reproduce:

```
python3 ../scripts/fact_guard.py answer-phantom.md --question-file q-phantom.txt
python3 ../scripts/fact_guard.py answer-correct.md --question-file q-phantom.txt
python3 ../scripts/fact_guard.py answer-auction-lots.md
python3 ../scripts/fact_guard.py answer-fictional-scores.md
```
