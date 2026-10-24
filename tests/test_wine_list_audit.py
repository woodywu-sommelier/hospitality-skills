import json
import re
import unittest

from helpers import SKILLS, TEST_YEAR, load_script

audit = load_script("wine-list-audit", "audit_list")
winelist = load_script("wine-list-audit", "winelist")
EXAMPLES = SKILLS / "wine-list-audit" / "examples"
REFERENCES = SKILLS / "wine-list-audit" / "references"


def run(list_text, menu_text=None, as_json=True, **kwargs):
    out = audit.run(list_text, menu_text, year=TEST_YEAR, title="test", as_json=as_json, **kwargs)
    return json.loads(out) if as_json else out


def titles(report, section):
    return [f["title"] for f in report[section]]


CSV_HEADER = "producer,name,region,grape,type,vintage,format,cost,price,btg,glass_price\n"


class ParserTests(unittest.TestCase):
    def test_csv_columns_are_read(self):
        wl = winelist.parse_wine_list(CSV_HEADER + "Maison Test,Cuvee A,Loire,Chenin Blanc,white,2022,75cl,12,48,yes,12\n")
        wine = wl.wines[0]
        self.assertEqual((wine.producer, wine.name, wine.vintage), ("Maison Test", "Cuvee A", "2022"))
        self.assertEqual((wine.cost, wine.price, wine.glass_price), (12, 48, 12))
        self.assertEqual(wine.format_ml, 750)
        self.assertTrue(wine.btg)
        self.assertEqual(wine.type, "white")

    def test_header_aliases_and_tabs(self):
        text = "Wine\tProducer\tYear\tMenu Price\tBy the glass\n" "Rosso\tTenuta Prova\t2020\t$60\t15\n"
        wine = winelist.parse_wine_list(text).wines[0]
        self.assertEqual((wine.name, wine.producer, wine.vintage, wine.price), ("Rosso", "Tenuta Prova", "2020", 60))
        self.assertTrue(wine.btg)
        self.assertEqual(wine.glass_price, 15)

    def test_plain_text_sections_and_slash_prices(self):
        text = "BY THE GLASS\nMaison Test, Brut, Champagne, NV, $20 / $95\nRED\nDomaine Test, Rouge, Loire, 2021, 1.5L, $140, cost $40\n"
        wines = winelist.parse_wine_list(text).wines
        self.assertEqual(len(wines), 2)
        self.assertTrue(wines[0].btg)
        self.assertEqual((wines[0].glass_price, wines[0].price, wines[0].vintage), (20, 95, "NV"))
        self.assertEqual(wines[0].type, "sparkling")
        self.assertEqual((wines[1].format_ml, wines[1].cost, wines[1].price), (1500, 40, 140))
        self.assertEqual(wines[1].type, "red")
        self.assertEqual(wines[1].region, "Loire")

    def test_missing_price_is_a_problem_not_a_guess(self):
        wines = winelist.parse_wine_list("RED\nDomaine Test, Rouge, Loire, 2015, market price\n").wines
        self.assertIsNone(wines[0].price)
        self.assertIn("no menu price", wines[0].problems)


class AuditTests(unittest.TestCase):
    def test_markup_below_band_uses_only_supplied_numbers(self):
        report = run(CSV_HEADER + "Maison A,Red One,Rioja,Tempranillo,red,2019,750ml,30,60,no,\n")
        fix = report["fix_first"][0]
        self.assertIn("below your markup band", fix["title"])
        line = fix["lines"][0]
        self.assertIn("cost $30, price $60, 2.00x", line)
        self.assertIn("$78", line)  # 30 x 2.6, the configured low band
        self.assertNotIn("total", line)

    def test_no_costs_means_no_markup_numbers(self):
        text = "RED\nDomaine A, Rouge, Loire, 2020, $50\nDomaine B, Rouge, Loire, 2020, $60\n"
        report = run(text)
        all_text = json.dumps(report)
        self.assertNotRegex(all_text, r"\d\.\d\dx")
        self.assertTrue(any("No costs were supplied" in m for m in report["missing"]))

    def test_custom_config_changes_bands(self):
        cfg = json.loads((REFERENCES / "pricing-defaults.json").read_text())
        for band in cfg["bottle_markup_bands"]["bands"]:
            band["low"], band["high"] = 1.5, 2.5
        path = REFERENCES.parent / "examples" / "_tmp_config.json"
        path.write_text(json.dumps(cfg))
        try:
            report = run(CSV_HEADER + "Maison A,Red One,Rioja,Tempranillo,red,2019,750ml,30,60,no,\n",
                         config_path=path)
        finally:
            path.unlink()
        self.assertFalse(report["fix_first"])

    def test_price_ladder_gap(self):
        rows = "".join(f"P{i},Wine {i},Rioja,Tempranillo,red,2019,750ml,,{p},no,\n"
                       for i, p in enumerate([40, 45, 50, 120, 130]))
        report = run(CSV_HEADER + rows)
        self.assertIn("Price gap in the list: nothing between $50 and $120",
                      titles(report, "fix_first") + titles(report, "worth_a_look"))

    def test_second_cheapest_thinnest_margin(self):
        rows = ("A,One,Rioja,Tempranillo,red,2019,750ml,10,40,no,\n"
                "B,Two,Rioja,Tempranillo,red,2019,750ml,30,50,no,\n"
                "C,Three,Rioja,Tempranillo,red,2019,750ml,20,70,no,\n"
                "D,Four,Rioja,Tempranillo,red,2019,750ml,25,90,no,\n")
        report = run(CSV_HEADER + rows)
        self.assertTrue(any("second-cheapest" in t and "thinnest margin" in t
                            for t in titles(report, "fix_first")))

    def test_btg_missing_red(self):
        rows = ("A,One,Sancerre,Sauvignon Blanc,white,2022,750ml,,50,yes,12\n"
                "B,Two,Rioja,Tempranillo,red,2019,750ml,,60,no,\n")
        report = run(CSV_HEADER + rows)
        self.assertIn("No reds by the glass", titles(report, "fix_first"))

    def test_menu_dish_without_pairing(self):
        rows = "A,One,Rioja,Tempranillo,red,2019,750ml,,60,yes,14\n"
        report = run(CSV_HEADER + rows, "DESSERT\nDark chocolate tart  14\nGrilled ribeye  60\n")
        fix = [f for f in report["fix_first"] if f["check"] == "menu"]
        self.assertEqual(len(fix), 1)
        self.assertIn("Dark chocolate tart", fix[0]["lines"][0])

    def test_no_menu_is_reported_missing(self):
        report = run(CSV_HEADER + "A,One,Rioja,Tempranillo,red,2019,750ml,,60,no,\n")
        self.assertTrue(any("No menu was supplied" in m for m in report["missing"]))

    def test_duplicates_and_near_duplicates(self):
        rows = ("Domaine A,Les Vignes,Loire,Chenin Blanc,white,2020,750ml,,50,no,\n"
                "Domaine A,Les Vignes,Loire,Chenin Blanc,white,2020,750ml,,55,no,\n"
                "Domaine B,Vieilles Vignes Blanc,Loire,Chenin Blanc,white,2020,750ml,,70,no,\n"
                "Domaine B,Vielles Vignes Blanc,Loire,Chenin Blanc,white,2020,750ml,,70,no,\n")
        report = run(CSV_HEADER + rows)
        self.assertIn("1 wine listed twice at different prices", titles(report, "fix_first"))
        self.assertTrue(any("near-duplicate" in t for t in titles(report, "worth_a_look")))

    def test_vintage_and_format_oddities(self):
        rows = ("A,One,Loire,Chenin Blanc,white,2031,750ml,,50,no,\n"
                "B,Two,Loire,Chenin Blanc,white,,750ml,,52,no,\n"
                "C,Three,Loire,Cabernet Franc,red,2019,750ml,,60,no,\n"
                "C,Three,Loire,Cabernet Franc,red,2019,375ml,,65,no,\n")
        report = run(CSV_HEADER + rows)
        self.assertIn("1 vintage later than 2026", titles(report, "fix_first"))
        self.assertIn("Half bottle priced at or above the full bottle", titles(report, "fix_first"))
        self.assertIn("1 still wine without a clear vintage", titles(report, "worth_a_look"))

    def test_report_order_and_closing_line(self):
        text = run(CSV_HEADER + "A,One,Rioja,Tempranillo,red,2019,750ml,30,60,no,\n", as_json=False)
        positions = [text.index(h) for h in ("## Fix first", "## Worth a look", "## Fine as is")]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(text.rstrip().endswith(audit.CLOSING_LINE))
        self.assertEqual(text.count(audit.CLOSING_LINE), 1)

    def test_examples_match_expected_reports(self):
        cases = [
            ("juniper-table-list.csv", "juniper-table-menu.txt", "The Juniper Table (fictional)",
             "juniper-table-expected-report.md"),
            ("bistro-lanterne-list.txt", None, "Bistro Lanterne (fictional)",
             "bistro-lanterne-expected-report.md"),
        ]
        for list_name, menu_name, title, expected in cases:
            with self.subTest(list_name):
                menu = (EXAMPLES / menu_name).read_text(encoding="utf-8") if menu_name else None
                out = audit.run((EXAMPLES / list_name).read_text(encoding="utf-8"), menu,
                                year=TEST_YEAR, title=title)
                self.assertEqual(out, (EXAMPLES / expected).read_text(encoding="utf-8"))

    def test_pricing_defaults_are_marked_unconfirmed(self):
        cfg = json.loads((REFERENCES / "pricing-defaults.json").read_text())
        self.assertIs(cfg["to_be_confirmed_by_woody"], True)
        for section in ("bottle_markup_bands", "by_the_glass", "price_ladder", "formats"):
            self.assertIs(cfg[section]["to_be_confirmed_by_woody"], True, section)
        rules = json.loads((REFERENCES / "pairing-rules.json").read_text())
        self.assertIs(rules["to_be_confirmed_by_woody"], True)

    def test_example_producers_are_fictional(self):
        fictional = {"Maison Imaginaire", "Cellier des Songes", "Domaine du Faux Puits",
                     "Weingut Erfunden", "Hollow Oak Cellars", "Clos des Chimères",
                     "Clos des Chimeres", "Tenuta Immaginaria", "Bodega Inventada",
                     "Fabled Hill Estate", "Château Nullepart", "Paper Moon Vineyards",
                     "Quinta Fictícia", "Copper Fig Kitchen"}
        for path in list(EXAMPLES.glob("*-list.*")) + list((SKILLS / "house-somm" / "examples").glob("*-list.*")):
            for wine in winelist.load_wine_list(path).wines:
                with self.subTest(path=path.name, line=wine.line_no):
                    self.assertIn(wine.producer, fictional)


if __name__ == "__main__":
    unittest.main()
