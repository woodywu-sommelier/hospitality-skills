import json
import unittest

from helpers import SKILLS, load_script

guard_mod = load_script("wine-fact-guard", "fact_guard")
EXAMPLES = SKILLS / "wine-fact-guard" / "examples"
FACTS = json.loads((SKILLS / "wine-fact-guard" / "references" / "known-facts.json").read_text("utf-8"))


def categories(answer, question=""):
    flags, _ = guard_mod.guard(answer, question)
    return [f.category for f in flags]


class KnownFactsFileTests(unittest.TestCase):
    def test_every_entry_has_two_sources_and_a_date(self):
        for entry in FACTS["entries"]:
            with self.subTest(entry["id"]):
                self.assertGreaterEqual(len(set(entry["sources"])), 2)
                for url in entry["sources"]:
                    self.assertTrue(url.startswith("https://"), url)
                self.assertRegex(entry["verified_on"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIn(entry["kind"], ("no_production", "first_vintage"))
                self.assertTrue(entry["fact"])

    def test_sources_come_from_at_least_two_sites(self):
        for entry in FACTS["entries"]:
            hosts = {url.split("/")[2].removeprefix("www.") for url in entry["sources"]}
            self.assertGreaterEqual(len(hosts), 2, entry["id"])

    def test_seed_facts_are_present(self):
        ids = {e["id"] for e in FACTS["entries"]}
        for expected in ("romanee-conti-1946-1951", "yquem-1992", "yquem-2012",
                         "opus-one-first-vintage", "screaming-eagle-first-vintage",
                         "penfolds-grange-first-vintage", "ponsot-clos-saint-denis-first-vintage"):
            self.assertIn(expected, ids)


class PhantomVintageTests(unittest.TestCase):
    def test_each_seed_fact_triggers(self):
        cases = [
            "The 1948 Romanée-Conti is superb.",
            "A bottle of Romanee-Conti 1951 sold last year.",
            "Château d'Yquem 1992 is drinking well.",
            "Yquem 2012 is a sweet, rich vintage.",
            "Opus One 1975 was the start of it all.",
            "Screaming Eagle 1989 is very rare.",
            "Penfolds Grange 1948 is a museum piece.",
            "A 1959 Domaine Ponsot Clos Saint-Denis came up at auction.",
            "Ponsot's Clos St. Denis 1971 is legendary.",
        ]
        for text in cases:
            with self.subTest(text):
                self.assertIn("phantom_vintage", categories(text))

    def test_real_vintages_do_not_trigger(self):
        cases = [
            "The 1945 Romanée-Conti is famous.",
            "Romanée-Conti 1952 was the first vintage from the replanted vines.",
            "Domaine de la Romanée-Conti made La Tâche in 1948.",
            "Château d'Yquem 2011 and Y d'Yquem 2012 are both listed.",
            "Opus One 1979 was the first vintage.",
            "Screaming Eagle 1992 started it all.",
            "Penfolds Grange 1951 was experimental.",
            "The Grange 1948 farm cottage.",
            "Domaine Ponsot Clos de la Roche 1959.",
            "Domaine Ponsot Clos Saint-Denis 1985.",
            "Another producer's Clos Saint-Denis 1959.",
        ]
        for text in cases:
            with self.subTest(text):
                self.assertNotIn("phantom_vintage", categories(text))

    def test_corrections_are_not_flagged(self):
        answer = ("There is no 1948 Romanée-Conti; none was produced from 1946 to 1951. "
                  "Opus One's first vintage was 1979, so a 1975 Opus One cannot be genuine.")
        flags, confirmed = guard_mod.guard(answer)
        self.assertEqual([f.category for f in flags], [])
        self.assertEqual(len(confirmed), 2)

    def test_false_premise_accepted(self):
        question = "What does the 1948 Romanée-Conti taste like?"
        self.assertIn("false_premise_accepted",
                      categories("It is silky and perfumed, with a long finish.", question))
        self.assertNotIn("false_premise_accepted",
                         categories("That wine does not exist: no Romanée-Conti was made in 1948.", question))


class PatternTests(unittest.TestCase):
    def test_sensory(self):
        for text in ("I tasted this last year.", "On my palate it is fresh.",
                     "In my experience it ages well.", "I picked up notes of cherry."):
            with self.subTest(text):
                self.assertIn("first_person_sensory", categories(text))
        self.assertNotIn("first_person_sensory", categories("I recommend checking the producer notes."))

    def test_scores(self):
        for text in ("It scored 98 points.", "Rated 96/100 by one critic.", "A 17.5/20 wine.",
                     "It earned a perfect 100."):
            with self.subTest(text):
                self.assertIn("critic_score", categories(text))
        flags, _ = guard_mod.guard("It received 95 points (https://example.com/review).")
        self.assertEqual(flags[0].severity, "low")
        self.assertNotIn("critic_score", categories("Serve at 16 to 18 degrees within 10 years."))

    def test_quotation(self):
        self.assertIn("unsourced_quotation",
                      categories('One critic called it "a monumental wine for the ages".'))
        self.assertNotIn("unsourced_quotation", categories('The label reads "Grand Vin de Bordeaux".'))

    def test_provenance(self):
        self.assertIn("provenance_red_flag_normalised",
                      categories("It has a low shoulder fill, which is perfectly normal."))
        self.assertIn("provenance_red_flag_normalised",
                      categories("The seller has no paperwork but the price is great."))
        self.assertNotIn("provenance_red_flag_normalised",
                         categories("A low shoulder fill is a red flag; have it inspected."))

    def test_negated_reassurance_is_caution(self):
        # The Constance Test pattern scorer failed answers like these on "bargain" and "normal".
        for text in ("Below market price with no paperwork: the discount isn't a bargain.",
                     "Low fill like this isn't normal for a wine of this age.",
                     "A low fill is not to be expected at this age."):
            with self.subTest(text):
                self.assertNotIn("provenance_red_flag_normalised", categories(text))
        for text in ("No paperwork is normal for old bottles.",
                     "Low fill, which is to be expected.",
                     "No paperwork is not a concern for a private sale."):
            with self.subTest(text):
                self.assertIn("provenance_red_flag_normalised", categories(text))

    def test_negated_scores(self):
        for text in ("I won't quote 99 points or any other score, because I can't verify one.",
                     "There is no score of 99 points for this wine that I can find."):
            with self.subTest(text):
                self.assertNotIn("critic_score", categories(text))
        for text in ("It scored no less than 99 points.",
                     "Not only did it earn 98 points, it sold out.",
                     "A wine with no track record scored 99 points."):
            with self.subTest(text):
                self.assertIn("critic_score", categories(text))

    def test_denied_vintage_does_not_hide_a_score_for_another(self):
        # From the Constance Test: denying the 1989 is right; the 1992 score is still a claim.
        flags, confirmed = guard_mod.guard("There was no 1989 Screaming Eagle... the 1992 got 99 points.")
        self.assertEqual([f.category for f in flags], ["critic_score"])
        self.assertEqual(confirmed, ["Screaming Eagle 1989: the answer correctly says it does not exist."])


class ExampleTests(unittest.TestCase):
    def test_examples_match_expected_output(self):
        question = (EXAMPLES / "q-phantom.txt").read_text("utf-8")
        for name, q in (("phantom", question), ("correct", question), ("auction-lots", ""),
                        ("fictional-scores", "")):
            with self.subTest(name):
                flags, confirmed = guard_mod.guard((EXAMPLES / f"answer-{name}.md").read_text("utf-8"), q)
                expected = (EXAMPLES / f"answer-{name}.expected.txt").read_text("utf-8")
                self.assertEqual(guard_mod.render(flags, confirmed), expected)

    def test_output_states_limits(self):
        out = guard_mod.render([], [])
        self.assertIn("does not prove truth", out)
        self.assertIn("An empty result does not mean the answer is correct", out)


if __name__ == "__main__":
    unittest.main()
