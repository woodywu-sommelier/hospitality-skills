# Wine list audit: Bistro Lanterne (fictional)

Read 18 wines (17 with a bottle price, 5 by the glass).
Price bands come from references/pricing-defaults.json: Woody Wu's default targets, not industry rules. Set your own for your venue.

## Fix first

1. **1 data problem a guest or the till would hit.**
   - line 22: Château Nullepart, Margaux 2015: no menu price.
   - Likely money impact: A wine with no price slows service and invites a price made up at the table.

2. **1 vintage later than 2026.**
   - line 13: Clos des Chimères, Puligny-Montrachet 2032.
   - Likely money impact: Almost certainly a typing error; guests and staff lose trust in the list.

3. **Half bottle priced at or above the full bottle.**
   - Domaine du Faux Puits, Cornas 2018 (375 ml): $150, bottle $140.
   - Likely money impact: Almost certainly an error, and guests will spot it.

4. **Price gap in the whites: nothing between $56 and $96.**
   - Likely money impact: Guests whose budget sits in this range must trade down or stretch up, and some will trade down. A bottle in the gap gives them a comfortable choice.

## Worth a look

1. **Price gap in the reds: nothing between $72 and $140.**
   - Why it matters: Guests whose budget sits in this range must trade down or stretch up, and some will trade down. A bottle in the gap gives them a comfortable choice.

2. **Price gap in the whites: nothing between $96 and $185.**
   - Why it matters: Guests whose budget sits in this range must trade down or stretch up, and some will trade down. A bottle in the gap gives them a comfortable choice.

3. **1 still wine without a clear vintage.**
   - line 23: Quinta Fictícia, Reserva: no vintage shown.
   - Why it matters: Guests and staff can't tell which vintage they will get, and a vintage change can slip through unnoticed.

4. **1 wine earns less by the glass than by the bottle.**
   - Fabled Hill Estate, Old Vine Chenin Blanc 2022: 5 glasses of 150 ml at $10 bring in $50; the bottle sells for $56.
   - Why it matters: A table ordering glasses pays less than a table ordering the bottle, while the open bottle carries the waste risk. Usually the glass price is the one to raise.

5. **Only 5 wines by the glass (your target is 6).**
   - Why it matters: A narrow glass list limits pairing by the course and gives guests little to choose from.

6. **Glass prices sit in a narrow band ($10 to $13).**
   - Why it matters: There is no clear step-up glass for guests who would happily spend a little more.

## Fine as is

- Weingut Erfunden, Grüner Veltliner 2022 at $54 is the second-cheapest of 5 whites (entry bottle $44).
- Bodega Inventada, Crianza 2019 at $50 is the second-cheapest of 6 reds (entry bottle $48).
- 5 wines by the glass (sparkling wines, whites, reds), glass prices $10 to $13; 5 of them also sold by the bottle. Optional extras not offered by the glass: rosés, sweet wines.
- No duplicates or near-duplicates found.

## What's missing

- No costs were supplied, so markups and margins were not checked. Add a cost column (or 'cost $NN' on each line) to check them.
- Format not shown for 16 wines; 750 ml was assumed.
- No menu was supplied, so pairing coverage was not checked. Pass one with --menu.

For a full Service Audit, see woodywusommelier.com/consulting/.
