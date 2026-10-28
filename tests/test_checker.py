import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import checker  # noqa: E402

EXAMPLES = {label: (answer, question) for label, answer, question in checker.EXAMPLES}


def categories(answer, question=""):
    return [f.category for f in checker.check(answer, question).flags]


class ExampleTests(unittest.TestCase):
    def test_dom_perignon_2001_example(self):
        answer, question = EXAMPLES["Describe the 2001 Dom Pérignon"]
        self.assertEqual(categories(answer, question), ["phantom_vintage", "false_premise_accepted",
                                                         "first_person_sensory", "critic_score"])

    def test_romanee_conti_1947_example(self):
        answer, question = EXAMPLES["1947 Romanée-Conti tasting note"]
        self.assertEqual(categories(answer, question), ["phantom_vintage", "false_premise_accepted",
                                                         "first_person_sensory", "critic_score"])

    def test_correct_example_is_clean(self):
        answer, question = EXAMPLES["A correct answer"]
        result = checker.check(answer, question)
        self.assertEqual(result.flags, [])
        self.assertEqual(result.handled,
                         ["Dom Pérignon 2001: the answer correctly says it does not exist."])

    def test_correct_2002_answer_has_no_flags(self):
        answer = ("Dom Pérignon 2002 is a vintage Champagne from a warm, even growing season. It is "
                  "usually described as rich and ripe, with notes of toast, citrus and stone fruit, "
                  "and good acidity for long ageing. For scores or tasting notes, check a published "
                  "review.")
        self.assertEqual(categories(answer, "Describe the 2002 Dom Pérignon."), [])


class InputTests(unittest.TestCase):
    def test_empty_input(self):
        for answer in ("", "   \n", None):
            with self.subTest(repr(answer)):
                result = checker.check(answer, "Describe the 2001 Dom Pérignon.")
                self.assertFalse(result.checked)
                self.assertEqual(result.notices, ["Paste an answer to check."])
                self.assertIn(checker.DISCLAIMER, checker.render(result))

    def test_long_input_is_capped_with_a_message(self):
        phantom = "The 2001 Dom Pérignon is lovely. "
        answer = phantom + "x" * 30_000 + " Rated 99/100."
        result = checker.check(answer)
        self.assertEqual(len(result.notices), 1)
        self.assertIn("Only the first 20,000 characters were checked", result.notices[0])
        cats = [f.category for f in result.flags]
        self.assertIn("phantom_vintage", cats)       # inside the first 20,000
        self.assertNotIn("critic_score", cats)       # past the cap, not checked
        self.assertIn("Only the first 20,000 characters", checker.run(answer))

    def test_input_at_the_cap_has_no_message(self):
        result = checker.check("a" * checker.MAX_CHARS)
        self.assertEqual(result.notices, [])

    def test_accents_are_optional(self):
        self.assertEqual(categories("The 2001 Dom Perignon is lovely."), ["phantom_vintage"])
        self.assertEqual(categories("The 1947 Romanee-Conti is lovely."), ["phantom_vintage"])


class RenderTests(unittest.TestCase):
    def test_card_shows_type_phrase_reason_and_sources(self):
        answer, question = EXAMPLES["Describe the 2001 Dom Pérignon"]
        page = checker.run(answer, question)
        self.assertIn("A wine that was never made", page)
        self.assertIn("The 2001 Dom Pérignon is a beautifully poised", page)
        self.assertIn("Dom Pérignon released no 2001 vintage", page)
        self.assertIn('href="https://en.wikipedia.org/wiki/Dom_P%C3%A9rignon"', page)
        self.assertIn("Found by a text pattern", page)
        self.assertTrue(page.removesuffix("</div>").endswith(checker.DISCLAIMER + "</p>"))

    def test_pasted_html_is_escaped(self):
        page = checker.run('<script>alert(1)</script> The 2001 Dom Pérignon <b>is great</b>.')
        self.assertNotIn("<script>", page)
        self.assertNotIn("<b>is great", page)
        self.assertIn("&lt;b&gt;", page)

    def test_clean_result_still_shows_the_disclaimer(self):
        page = checker.run("Serve Champagne well chilled.")
        self.assertIn("Nothing flagged.", page)
        self.assertIn(checker.DISCLAIMER, page)


class RuleTests(unittest.TestCase):
    def test_no_em_or_en_dashes(self):
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".json", ".txt"} and ".git" not in path.parts:
                text = path.read_text(encoding="utf-8")
                for ch in (chr(0x2014), chr(0x2013)):
                    self.assertNotIn(ch, text, str(path.relative_to(ROOT)))

    def test_no_network_or_model_calls(self):
        banned = {"requests", "httpx", "urllib.request", "http.client", "socket", "openai",
                  "anthropic", "huggingface_hub", "subprocess"}
        for name in ("app.py", "checker.py", "vendor/wine-fact-guard/scripts/fact_guard.py"):
            tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = ([a.name for a in node.names] if isinstance(node, ast.Import)
                        else [node.module] if isinstance(node, ast.ImportFrom) else [])
                for mod in mods:
                    self.assertNotIn(mod, banned, f"{mod} imported in {name}")

    def test_vendored_files_are_recorded_in_the_readme(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("de644a6e2dd5ffa3460551c654012cd5c1eb6395", readme)


@unittest.skipUnless(__import__("importlib").util.find_spec("gradio"), "gradio not installed")
class PrivacyTests(unittest.TestCase):
    def test_app_turns_off_telemetry_run_history_and_monitoring(self):
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        for setting in ('os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"',
                        'os.environ["GRADIO_RUN_HISTORY"] = "False"', "analytics_enabled=False",
                        "run_history=False", "enable_monitoring=False", "cache_examples=False"):
            self.assertIn(setting, source)
        import app
        self.assertFalse(app.demo.analytics_enabled)


if __name__ == "__main__":
    unittest.main()
