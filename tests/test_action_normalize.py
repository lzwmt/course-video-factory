#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.action_normalize import PLAYER_TYPES, normalize_action, normalize_scene_actions
from scripts.compile_chapter import ChapterCompiler
from scripts.generate_compositions import generate_all_compositions


def test_show_title_maps_to_enter_title():
    act = normalize_action(
        {"type": "show_title", "target": "stage_canvas", "params": {"title": "X"}},
        {"scene_type": "hook"},
    )
    assert act["type"] == "enter"
    assert act["target"] == "#title"
    assert act["title"] == "X"


def test_render_component_maps_to_add_node():
    act = normalize_action(
        {"type": "render_component", "target": "single_box"},
        {"graph": {"nodes": ["single"]}},
    )
    assert act["type"] == "add_node"
    assert act["target"] == "single"


def test_packet_without_endpoints_falls_back():
    act = normalize_action({"type": "show_data_flow"}, {"graph": {"nodes": ["client", "web"]}})
    assert act["type"] == "reveal_graph"


def test_compile_ch01_actions_are_playable():
    course = "system-design" if (ROOT / "content" / "courses" / "system-design").exists() else "demo"
    out = ChapterCompiler(course_id=course).compile_target(chapter_id="01")
    import json

    spec = json.loads(out.read_text(encoding="utf-8"))
    unknown = []
    for scene in spec["scenes"]:
        normalize_scene_actions(scene)
        for act in scene.get("actions") or []:
            if act.get("type") not in PLAYER_TYPES:
                unknown.append(act)
    assert not unknown, unknown


def test_generate_html_has_known_actions():
    import json
    from tempfile import TemporaryDirectory

    course = "system-design" if (ROOT / "content" / "courses" / "system-design").exists() else "demo"
    compiler = ChapterCompiler(course_id=course)
    spec_path = compiler.compile_target(chapter_id="01")
    htmls = generate_all_compositions(spec_path)
    text = htmls[0].read_text(encoding="utf-8")
    assert "show_title" not in text or '"type": "enter"' in text or '"type":"enter"' in text
    assert "playActions(tl, SCENE.actions" in text


if __name__ == "__main__":
    test_show_title_maps_to_enter_title()
    test_render_component_maps_to_add_node()
    test_packet_without_endpoints_falls_back()
    test_compile_ch01_actions_are_playable()
    test_generate_html_has_known_actions()
    print("ok")
