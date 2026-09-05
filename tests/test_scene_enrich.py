#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.scene_enrich import enrich_scene, infer_graph, localize_text
from scripts.compile_chapter import ChapterCompiler


def test_localize_glossary_and_strip_html():
    s = localize_text('Section 1: Single Server Setup <img src="x.png">')
    assert "单机部署" in s
    assert "<img" not in s


def test_infer_graph_from_cache_text():
    g = infer_graph("引入 Redis 缓存挡住数据库")
    assert "redis" in g["nodes"]


def test_empty_scene_filled_from_source():
    scene = {"scene": "02", "scene_type": "problem", "actions": []}
    source = "网站刚上线时，Web 应用、数据库和缓存通常跑在同一台服务器上。用户通过域名做 DNS 解析。"
    enrich_scene(scene, source_text=source, next_title="数据库分离", badge_prefix="系统设计全书")
    assert scene["narration"]
    assert all("\u4e00" <= ch <= "\u9fff" or not ch.isalpha() for ch in scene["title"])
    assert scene["graph"]["nodes"]
    assert any(a.get("type") in ("add_node", "packet", "reveal_graph") for a in scene["actions"])


def test_compile_section_dynamic():
    import json
    course = "system-design" if (ROOT / "content" / "courses" / "system-design").exists() else "demo"
    compiler = ChapterCompiler(course_id=course)
    if course == "system-design":
        out = compiler.compile_target(section_id="01-S01")
    else:
        out = compiler.compile_target(chapter_id="01")
    spec = json.loads(out.read_text(encoding="utf-8"))
    assert 3 <= len(spec["scenes"]) <= 8
    for sc in spec["scenes"]:
        assert sc.get("narration")
        assert "<" not in sc["narration"]
        if sc.get("scene_type") in ("problem", "flow", "evolve"):
            assert (sc.get("graph") or {}).get("nodes")
            assert sc.get("actions")


if __name__ == "__main__":
    test_localize_glossary_and_strip_html()
    test_infer_graph_from_cache_text()
    test_empty_scene_filled_from_source()
    test_compile_section_dynamic()
    print("ok")
