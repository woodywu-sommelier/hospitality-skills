"""Shared test helpers: load skill scripts by path (skill folders have dashes)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
TEST_YEAR = 2026


def load_script(skill: str, module: str):
    """Import skills/<skill>/scripts/<module>.py as a fresh module."""
    scripts = SKILLS / skill / "scripts"
    name = f"{skill.replace('-', '_')}_{module}"
    if name in sys.modules:
        return sys.modules[name]
    # Each skill ships its own winelist.py; make sure the right copy is imported.
    sys.modules.pop("winelist", None)
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location(name, scripts / f"{module}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(scripts))
    return mod
