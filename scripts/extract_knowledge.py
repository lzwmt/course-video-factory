#!/usr/bin/env python3
"""Extract a traceable, deterministic knowledge skeleton from a chapter Markdown file.
The skeleton is fed to the LLM; every item retains a source excerpt for review.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def extract(path: Path, chapter_id: str) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    headings = []
    for i, line in enumerate(lines):
        if re.match(r"^#{1,3}\s+", line):
            title = re.sub(r"^#{1,3}\s+", "", line).strip(" *")
            if title.lower() not in {"introduction", "conclusion", "summary"}:
                excerpt = " ".join(x.strip() for x in lines[i:min(i + 5, len(lines))] if x.strip())
                headings.append({"name": title, "source_excerpt": excerpt[:600]})
    formulas = []
    for line in lines:
        if any(x in line for x in ("=", "≈", "×", "÷", "O(", "2^")) and len(line.strip()) < 500:
            formulas.append({"formula": re.sub(r"[*`]", "", line).strip(), "source_excerpt": line.strip()})
    # Keep the source faithful: this is an index, not an invented summary.
    return {
        "chapter_id": chapter_id,
        "source_file": str(path),
        "requirements": {"functional": [], "non_functional": []},
        "topics": headings[:30],
        "formulas": formulas[:30],
        "components": [], "data_flows": [], "algorithms": [],
        "failure_scenarios": [], "tradeoffs": [], "key_takeaways": [],
        "uncertainties": ["需要模型根据 source_excerpt 补全并逐项保留原文依据"]
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--chapter", required=True)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    out = a.output or ROOT / "content" / "chapters" / a.chapter / "knowledge.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(extract(a.input, a.chapter), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)

if __name__ == "__main__":
    main()
