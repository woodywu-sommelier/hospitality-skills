# Examples

Everything here is fictional. The venues (The Juniper Table, Bistro Lanterne) and every producer (Maison Imaginaire, Domaine du Faux Puits, Château Nullepart and the rest) are invented for testing. Regions and grapes are real so the style checks have something to read. Prices and costs are made up and say nothing about any real wine.

| File | What it shows |
| --- | --- |
| `juniper-table-list.csv` | A CSV list with costs and by-the-glass prices. Planted issues: a duplicate at two prices, a thin-margin second-cheapest red, glass prices under bottle cost, a price gap, a spelling variant, a missing vintage, an underpriced magnum, mixed format notation. |
| `juniper-table-menu.txt` | A short menu for the list above, including a chocolate dessert with nothing sweet on the list. |
| `juniper-table-expected-report.md` | The report the script produces for the two files above. |
| `bistro-lanterne-list.txt` | A pasted-text list with no costs and no menu. Planted issues: a wine with no price, a vintage in the future, a half bottle priced above the bottle, a glass price that earns less than the bottle. |
| `bistro-lanterne-expected-report.md` | The report for the list above, including what was skipped because data was missing. |

Regenerate the reports with:

```
python3 ../scripts/audit_list.py juniper-table-list.csv --menu juniper-table-menu.txt --year 2026 --title "The Juniper Table (fictional)" > juniper-table-expected-report.md
python3 ../scripts/audit_list.py bistro-lanterne-list.txt --year 2026 --title "Bistro Lanterne (fictional)" > bistro-lanterne-expected-report.md
```
