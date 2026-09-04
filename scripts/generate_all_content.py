#!/usr/bin/env python3
"""Generate each chapter from its source Markdown, stopping on the first failure.
AI calls are intentionally serial so a failed chapter can be reviewed before continuing.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def source_for(chapter_id: str) -> Path:
    matches = sorted((ROOT / "content" / "source").glob(f"{chapter_id.zfill(2)}-*.md"))
    if not matches:
        raise FileNotFoundError(f"No source Markdown for chapter {chapter_id}")
    return matches[0]

def main() -> None:
    p = argparse.ArgumentParser(description="Serial source-driven AI chapter generation")
    p.add_argument("--course", default="demo")
    p.add_argument("--only", help="one chapter id, e.g. 04")
    p.add_argument("--from-chapter", default="01")
    p.add_argument("--max-retries", type=int, default=3)
    args = p.parse_args()
    catalog = json.loads((ROOT / "data" / "chapter_list.json").read_text(encoding="utf-8"))
    selected = catalog["chapters"]
    if args.only:
        selected = [x for x in selected if str(x["id"]) == args.only.zfill(2)]
    else:
        selected = [x for x in selected if str(x["id"]) >= args.from_chapter.zfill(2)]
    for item in selected:
        cid = str(item["id"])
        source = source_for(cid)
        print(f"\n=== chapter {cid}: {item['title_zh']} ===", flush=True)
        cmd = [sys.executable, str(ROOT / "scripts" / "ai_author.py"), "--course", args.course,
               "--chapter", cid, "--input", str(source)]
        cmd += ["--max-retries", str(args.max_retries)]
        # Each chapter must pass the compiler gate before the next one starts.
        subprocess.run(cmd, cwd=ROOT, check=True)
        print(f"[generate_all_content] chapter {cid} passed compile gate", flush=True)

if __name__ == "__main__":
    main()
