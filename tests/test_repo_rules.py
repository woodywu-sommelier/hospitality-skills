"""House rules for everything published from this repository."""
import ast
import re
import sys
import unittest

from helpers import ROOT, SKILLS

TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".csv", ".cff", ".jsonl", ""}
SKIP_DIRS = {".git", "dist", "__pycache__"}


def text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in TEXT_SUFFIXES or path.name.startswith("LICENSE"):
            yield path


def prose_lines(path):
    """Markdown lines outside fenced code blocks."""
    in_code = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            yield number, line


class ContentRules(unittest.TestCase):
    def test_no_em_or_en_dashes(self):
        for path in text_files():
            text = path.read_text(encoding="utf-8")
            for ch, name in ((chr(0x2014), "em dash"), (chr(0x2013), "en dash")):
                self.assertNotIn(ch, text, f"{name} in {path.relative_to(ROOT)}")

    def test_no_hyphens_used_as_dashes_in_prose(self):
        for path in ROOT.rglob("*.md"):
            if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
                continue
            for number, line in prose_lines(path):
                body = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line)
                body = re.sub(r"`[^`]*`", "", body)
                with self.subTest(f"{path.relative_to(ROOT)}:{number}"):
                    self.assertNotRegex(body, r"\s--?\s")

    def test_no_secrets(self):
        patterns = [r"sk-[A-Za-z0-9_-]{20,}", r"\bhf_[A-Za-z0-9]{20,}", r"\bghp_[A-Za-z0-9]{20,}",
                    r"\bAKIA[0-9A-Z]{16}\b", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
                    r"(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{12,}['\"]"]
        for path in text_files():
            text = path.read_text(encoding="utf-8")
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, text), f"{pattern} in {path.relative_to(ROOT)}")

    def test_no_age_hints(self):
        phrases = ["years of experience", "decades", "veteran", "born in", "graduated in",
                   "since 19", "since 20"]
        for path in text_files():
            if path.parent.name == "tests":
                continue
            text = path.read_text(encoding="utf-8").lower()
            for phrase in phrases:
                self.assertNotIn(phrase, text, f"'{phrase}' in {path.relative_to(ROOT)}")

    def test_real_producers_only_in_sourced_facts(self):
        names = ["Romanée-Conti", "Romanee-Conti", "Yquem", "Opus One", "Screaming Eagle",
                 "Penfolds", "Ponsot", "Dom Pérignon", "Dom Perignon"]
        allowed = {SKILLS / "wine-fact-guard", ROOT / "tests"}
        for path in text_files():
            if any(base in path.parents for base in allowed):
                continue
            text = path.read_text(encoding="utf-8")
            for name in names:
                self.assertNotIn(name, text, f"{name} in {path.relative_to(ROOT)}")


class SkillFormat(unittest.TestCase):
    SERVICE_LINKS = {
        "wine-list-audit": "woodywusommelier.com/consulting/",
        "house-somm": "concierge.woodywusommelier.com",
        "wine-fact-guard": "woodywusommelier.com/consulting/ai-teams/",
    }

    def test_front_matter(self):
        skills = sorted(p for p in SKILLS.iterdir() if p.is_dir())
        self.assertEqual([p.name for p in skills], sorted(self.SERVICE_LINKS))
        for skill in skills:
            with self.subTest(skill.name):
                text = (skill / "SKILL.md").read_text(encoding="utf-8")
                match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
                self.assertIsNotNone(match)
                fields = dict(line.split(": ", 1) for line in match.group(1).splitlines())
                self.assertEqual(fields["name"], skill.name)
                self.assertRegex(fields["name"], r"^[a-z0-9-]{1,64}$")
                self.assertIn("Use when", fields["description"])
                self.assertLessEqual(len(fields["description"]), 1024)

    def test_each_skill_points_to_its_service(self):
        for skill, link in self.SERVICE_LINKS.items():
            text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn(link, text, skill)

    def test_readme_links(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for link in ("https://woodywusommelier.com", "https://woodywusommelier.com/consulting/",
                     "https://concierge.woodywusommelier.com",
                     "https://woodywusommelier.com/consulting/ai-teams/", "$3,500 CAD",
                     "The Constance Test"):
            self.assertIn(link, text)

    def test_root_files(self):
        for name in ("README.md", "LICENSE", "LICENSE-DATA", "CITATION.cff"):
            self.assertTrue((ROOT / name).is_file(), name)
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())
        self.assertIn("CC BY 4.0", (ROOT / "LICENSE-DATA").read_text())


class ScriptRules(unittest.TestCase):
    def test_standard_library_only(self):
        local = {"winelist", "helpers"}
        stdlib = set(sys.stdlib_module_names)
        for path in ROOT.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    top = module.split(".")[0]
                    if top.startswith("test_"):
                        continue
                    self.assertTrue(top in stdlib or top in local or top == "__future__",
                                    f"{top} imported in {path.relative_to(ROOT)}")

    def test_readme_excerpt_matches_real_output(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        report = (SKILLS / "wine-list-audit" / "examples" / "juniper-table-expected-report.md").read_text("utf-8")
        excerpt = readme.split("## For owners and managers", 1)[1].split("```")[1]
        for line in excerpt.strip().splitlines():
            if line.strip():
                self.assertIn(line, report)


if __name__ == "__main__":
    unittest.main()
