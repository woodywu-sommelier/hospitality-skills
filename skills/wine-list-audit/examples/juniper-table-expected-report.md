# Wine list audit: The Juniper Table (fictional)

Read 19 wines (19 with a bottle price, 6 by the glass). Menu: 11 dishes.
Price bands come from references/pricing-defaults.json. They are starting assumptions to be confirmed, not industry facts.

## Fix first

1. **1 wine listed twice at different prices.**
   - Bodega Inventada, Reserva 2018: line 13: $74; line 19: $78.
   - Likely money impact: Guests and staff see two prices for one wine, and a guest who has seen the lower price will expect it.

2. **2 bottles priced below your markup band.**
   - Paper Moon Vineyards, Pinot Noir 2021: cost $26, price $64, 2.46x (your band 2.6x to 3.5x). At 2.6x the price would be $67.60, $3.60 more per bottle sold.
   - Weingut Erfunden, Kabinett 2022: cost $17, price $48, 2.82x (your band 3.0x to 4.0x). At 3.0x the price would be $51, $3 more per bottle sold.
   - Likely money impact: Margin is given away on every one of these bottles sold. No sales volumes were supplied, so only the gap per bottle is shown, not a total.

3. **2 glass prices below the cost of the bottle.**
   - Château Nullepart, Cuvée Classique 2019: glass $13, bottle cost $16.
   - Paper Moon Vineyards, Pinot Noir 2021: glass $18, bottle cost $26.
   - Likely money impact: The first glass does not cover the bottle, so every open bottle depends on selling later pours before it fades. Any waste turns straight into loss.

4. **The second-cheapest red has the thinnest margin on the whole list.**
   - Paper Moon Vineyards, Pinot Noir 2021 at $64 is the second-cheapest of 8 reds (entry bottle $52). Cost $26: 2.46x, margin 59%.
   - Likely money impact: The second-cheapest bottle is often a popular pick (check your own sales mix to confirm). If it is here, this thin margin repeats on a large share of bottles sold.

5. **1 dish with no sensible pairing on the list.**
   - Dark chocolate tart (chocolate desserts and fruit and pastry desserts): nothing fortified or sweet on the list.
   - Likely money impact: Guests ordering these dishes either drink something that fights the food or skip wine, and staff have nothing confident to suggest.

6. **Price gap in the reds: nothing between $78 and $135.**
   - Likely money impact: Guests whose budget sits in this range must trade down or stretch up, and some will trade down. A bottle in the gap gives them a comfortable choice.

## Worth a look

1. **Price gap in the whites: nothing between $98 and $175.**
   - Why it matters: Guests whose budget sits in this range must trade down or stretch up, and some will trade down. A bottle in the gap gives them a comfortable choice.

2. **1 bottle priced above your markup band.**
   - Fabled Hill Estate, Dry Rosé 2023: cost $14, price $58, 4.14x (your band 3.0x to 4.0x).
   - Why it matters: Guests who know retail prices may read these as poor value, which can slow sales. Without sales data this is a risk, not a measured loss.

3. **Magnum priced under your multiple of the bottle price.**
   - Château Nullepart, Grand Vin 2016 (1500 ml): $290 against $160 for the bottle. At 2x the bottle it would be $320, $30 more.
   - Why it matters: A magnum costs more to buy and to hold than two bottles; underpricing it gives away margin on a special-occasion sale.

4. **1 still wine without a clear vintage.**
   - line 8: Tenuta Immaginaria, Bianco di Collina: no vintage shown.
   - Why it matters: Guests and staff can't tell which vintage they will get, and a vintage change can slip through unnoticed.

5. **1 dish pairs by the bottle only.**
   - Mushroom risotto (mushrooms and earthy flavours and cream and butter sauces): 3 matches by the bottle, none by the glass.
   - Why it matters: A guest who wants one glass with this dish has no good match.

6. **No sparkling wines by the glass.**
   - Why it matters: A glass of sparkling is a common way to start a meal; without one the opening order often goes to something lower value.

7. **Glass prices sit in a narrow band ($13 to $19).**
   - Why it matters: There is no clear step-up glass for guests who would happily spend a little more.

8. **1 possible near-duplicate or spelling variant.**
   - line 7 'Clos des Chimères, Vieilles Vignes 2020' and line 20 'Clos des Chimeres, Vielles Vignes 2020'.
   - Why it matters: Usually a typo, which makes the list look careless and can confuse stock counts.

9. **Formats are written 3 different ways (1.5L, 750ml, 75cl).**
   - Why it matters: Small, but a consistent list reads as a careful one.

## Fine as is

- Every line was read with a name and a price.
- 16 of 19 costed bottles sit inside your markup bands.
- Tenuta Immaginaria, Bianco di Collina at $52 is the second-cheapest of 7 whites (entry bottle $48). Cost $15: 3.47x, margin 71%. Its margin is neither the thinnest nor the steepest.
- 6 wines by the glass (whites, rosés, reds), glass prices $13 to $19; 6 of them also sold by the bottle. Optional extras not offered by the glass: sweet wines.
- 8 of 11 dishes have at least one sensible match by the glass.

## What's missing

- Could not classify 1 dish, so check it by hand: Lemon posset.
- Style could not be read for 1 wine (no grape or region the rules recognise), so menu coverage may be understated: Tenuta Immaginaria, Bianco di Collina.

For a full Service Audit, see woodywusommelier.com/consulting/.
