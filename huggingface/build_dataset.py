#!/usr/bin/env python3
"""Assemble the Hugging Face dataset folder from files in this repository.

Usage:
    python3 huggingface/build_dataset.py [OUT_DIR]

Writes to dist/hf-dataset by default. Standard library only. Uploading is a
separate, manual step (see huggingface/README.md).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

FILES = {
    "README.md": ROOT / "huggingface" / "dataset-card.md",
    "LICENSE-DATA": ROOT / "LICENSE-DATA",
    "known-facts/known-facts.json": SKILLS / "wine-fact-guard" / "references" / "known-facts.json",
    "wine-lists/juniper-table-list.csv": SKILLS / "wine-list-audit" / "examples" / "juniper-table-list.csv",
    "wine-lists/juniper-table-menu.txt": SKILLS / "wine-list-audit" / "examples" / "juniper-table-menu.txt",
    "wine-lists/juniper-table-expected-report.md": SKILLS / "wine-list-audit" / "examples" / "juniper-table-expected-report.md",
    "wine-lists/bistro-lanterne-list.txt": SKILLS / "wine-list-audit" / "examples" / "bistro-lanterne-list.txt",
    "wine-lists/bistro-lanterne-expected-report.md": SKILLS / "wine-list-audit" / "examples" / "bistro-lanterne-expected-report.md",
    "wine-lists/copper-fig-list.csv": SKILLS / "house-somm" / "examples" / "copper-fig-list.csv",
}


def build(out_dir: Path) -> list[Path]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    written = []
    for relative, source in FILES.items():
        target = out_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        written.append(target)
    facts = json.loads(FILES["known-facts/known-facts.json"].read_text(encoding="utf-8"))
    jsonl = out_dir / "known-facts" / "known-facts.jsonl"
    with jsonl.open("w", encoding="utf-8") as handle:
        for entry in facts["entries"]:
            row = {"years": None, "first_vintage": None, "notes": None, **entry}
            row["match"] = json.dumps(entry["match"], ensure_ascii=False)
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    written.append(jsonl)
    return written


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "hf-dataset"
    for path in build(out_dir):
        print(path.relative_to(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
