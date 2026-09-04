#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.compile_chapter import ChapterCompiler
from scripts.presenter_paths import studio_root


def test_demo_compiles():
    out = ChapterCompiler(course_id="demo").compile_target(chapter_id="01")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Demo" in text
    assert "sharded" in text.lower() or "分片" in text


def test_studio_not_hardcoded_home():
    src = (ROOT / "scripts" / "produce_pipeline.py").read_text(encoding="utf-8")
    assert "/home/lzwmt/project/ai-presenter-studio" not in src
    src2 = (ROOT / "scripts" / "build_timed_shots.py").read_text(encoding="utf-8")
    assert "/home/lzwmt/project/ai-presenter-studio" not in src2
    # sibling layout is allowed; env overrides
    _ = studio_root()


if __name__ == "__main__":
    test_demo_compiles()
    test_studio_not_hardcoded_home()
    print("ok")
