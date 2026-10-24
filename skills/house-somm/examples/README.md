# Examples

Everything here is fictional: the venue (The Copper Fig) and every producer on its list are invented. Regions and grapes are real so the recommendations make sense.

| File | What it shows |
| --- | --- |
| `copper-fig-list.csv` | A fictional list with bottle and glass prices, a high-value bottle, and an alcohol-free option. |
| `conversations.md` | Seven guest requests and replies that follow the rules: budget not stated, nothing fits, a glass instead of a bottle, a guest not drinking, an allergy, a possibly faulty bottle, a high-value bottle. All pass the checker. |
| `reply-good.md` / `.expected.txt` | A good reply and the checker's clean result. |
| `reply-bad-invented.md` / `.expected.txt` | A reply that invents a wine, changes a vintage and a price, and makes first-person tasting claims. |
| `reply-bad-escalation.md` / `.expected.txt` | A reply that recommends a high-value bottle and answers an allergy question without bringing in a person, and nudges the guest to drink more. |

Reproduce the outputs:

```
python3 ../scripts/check_reply.py --list copper-fig-list.csv --reply reply-good.md
python3 ../scripts/check_reply.py --list copper-fig-list.csv --reply reply-bad-invented.md
python3 ../scripts/check_reply.py --list copper-fig-list.csv --reply reply-bad-escalation.md --guest "We're celebrating tonight. What's your best Bordeaux? My partner has a sulfite allergy."
```
