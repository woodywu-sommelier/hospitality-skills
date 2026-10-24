import re
import unittest

from helpers import SKILLS, load_script

check = load_script("house-somm", "check_reply")
winelist = load_script("house-somm", "winelist")
EXAMPLES = SKILLS / "house-somm" / "examples"
WINES = winelist.load_wine_list(EXAMPLES / "copper-fig-list.csv").wines


def kinds(reply, guest=""):
    flags, _ = check.check_reply(reply, WINES, guest)
    return [f.kind for f in flags]


class CheckReplyTests(unittest.TestCase):
    def test_exact_quote_passes(self):
        reply = "Try the Domaine du Faux Puits Les Cailloux 2023 ($74, or $17 a glass)."
        self.assertEqual(kinds(reply), [])

    def test_invented_wine_is_flagged(self):
        self.assertIn("not_on_list", kinds("I'd pour the Domaine Hors-Liste 2015 with the duck."))
        self.assertIn("not_on_list", kinds("The Inventive Ridge Cellars Syrah is perfect here."))

    def test_wrong_vintage_and_price_are_flagged(self):
        reply = "The Paper Moon Vineyards Hillside Pinot Noir 2019 at $78 suits the duck."
        found = kinds(reply)
        self.assertIn("vintage_mismatch", found)
        self.assertIn("price_mismatch", found)

    def test_glass_price_is_accepted(self):
        reply = "The Weingut Erfunden Steinterrassen Riesling Kabinett 2022 is $14 a glass or $58 a bottle."
        self.assertEqual(kinds(reply), [])

    def test_budget_amounts_are_not_price_errors(self):
        reply = ("To stay under $80, the Tenuta Immaginaria Rosso di Collina 2020 ($72, or $16 a "
                 "glass) works well.")
        self.assertEqual(kinds(reply), [])

    def test_incomplete_quote_is_flagged(self):
        self.assertIn("incomplete_quote", kinds("The Hollow Oak Cellars Reserve Chardonnay is lovely here."))

    def test_sensory_claims_are_flagged(self):
        for phrase in ("When I tasted it, it was silky.", "On my palate it is round.",
                       "It is my favourite on the list.", "I picked up notes of plum."):
            with self.subTest(phrase):
                self.assertIn("sensory_claim", kinds(phrase))

    def test_recommend_is_not_a_sensory_claim(self):
        self.assertNotIn("sensory_claim", kinds("I'd suggest something crisp. I recommend a glass of white."))

    def test_high_value_bottle_needs_handoff(self):
        reply = "The Château Nullepart Grand Vin 2016 ($340) is the showpiece."
        self.assertIn("escalation_missing", kinds(reply))
        self.assertNotIn("escalation_missing",
                         kinds(reply + " Shall I ask our sommelier to come over?"))

    def test_allergy_and_off_bottle_need_handoff(self):
        self.assertIn("escalation_missing", kinds("Any of our whites will be fine.", "I'm allergic to sulfites"))
        self.assertIn("escalation_missing", kinds("Sorry to hear that!", "This bottle is corked."))
        self.assertEqual(kinds("I'm sorry. A member of the team will be right with you.", "This bottle is corked."), [])

    def test_pushing_drinks_is_flagged(self):
        self.assertIn("pushes_drinking", kinds("Why not another bottle with dessert?"))

    def test_example_outputs_match(self):
        guest = ("We're celebrating tonight. What's your best Bordeaux? "
                 "My partner has a sulfite allergy.")
        for name, guest_text in (("reply-good", ""), ("reply-bad-invented", ""),
                                 ("reply-bad-escalation", guest)):
            with self.subTest(name):
                reply = (EXAMPLES / f"{name}.md").read_text(encoding="utf-8")
                flags, matches = check.check_reply(reply, WINES, guest_text)
                out = check.render(flags, matches, len(WINES))
                self.assertEqual(out, (EXAMPLES / f"{name}.expected.txt").read_text(encoding="utf-8"))

    def test_bad_examples_fail_and_good_passes(self):
        self.assertEqual(kinds((EXAMPLES / "reply-good.md").read_text()), [])
        bad = kinds((EXAMPLES / "reply-bad-invented.md").read_text())
        for kind in ("not_on_list", "vintage_mismatch", "price_mismatch", "sensory_claim"):
            self.assertIn(kind, bad)

    def test_sample_conversations_pass(self):
        text = (EXAMPLES / "conversations.md").read_text(encoding="utf-8")
        pairs = re.findall(r"\*\*Guest:\*\* (.+?)\n\n\*\*Assistant:\*\* (.+?)\n", text)
        self.assertEqual(len(pairs), 7)
        for guest, reply in pairs:
            with self.subTest(guest):
                self.assertEqual(kinds(reply, guest), [])

    def test_shared_parser_copies_are_identical(self):
        a = (SKILLS / "wine-list-audit" / "scripts" / "winelist.py").read_bytes()
        b = (SKILLS / "house-somm" / "scripts" / "winelist.py").read_bytes()
        self.assertEqual(a, b, "Keep the two winelist.py copies identical.")


if __name__ == "__main__":
    unittest.main()
