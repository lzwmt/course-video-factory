"""Normalize author-facing action DSL onto playActions() types."""
from __future__ import annotations

PLAYER_TYPES = {
    "enter",
    "add_node",
    "node",
    "reveal_graph",
    "connect",
    "packet",
    "highlight",
    "metric",
    "counter",
    "alert",
    "zoom",
    "focus",
    "code_line",
    "term_line",
    "card",
    "split_node",
    "scale_node",
    "calc_show_step",
    "show_step",
    "calc_roll_result",
    "roll_result",
    "calc_show_formula",
    "show_formula",
    "calc_show_assumption",
    "show_assumption",
    "assumption_card",
    "calc_show_ladder",
    "show_ladder",
    "ladder_step",
    "ring_init",
    "ring_route",
    "ring_node_down",
    "ring_add_node",
    "bucket_refill",
    "bucket_consume",
    "bucket_reject",
    "window_slide",
    "move_pointer",
    "highlight_item",
    "detach_node",
    "insert_head",
    "remove_tail",
    "map_put",
    "map_highlight",
    "map_delete",
    "traverse_path",
    "pulse_node",
    "push_stack",
    "pop_stack",
    "fill_cell",
}

TYPE_ALIASES = {
    "show_title": "enter",
    "show_text": "enter",
    "show_component": "add_node",
    "render_component": "add_node",
    "insert_layer": "add_node",
    "update_architecture": "reveal_graph",
    "scale_global": "scale_node",
    "show_architecture_diff": "reveal_graph",
    "show_architecture_shift": "reveal_graph",
    "show_architecture_recap": "reveal_graph",
    "show_diagram": "reveal_graph",
    "show_flowchart": "reveal_graph",
    "show_pipeline": "reveal_graph",
    "show_comparison": "enter",
    "show_data_flow": "packet",
    "trace_data_flow": "packet",
    "trace_sequence_flow": "packet",
    "show_flow_split": "reveal_graph",
    "show_ha_and_multicast": "reveal_graph",
    "highlight_summary": "card",
    "highlight_summary_points": "card",
    "highlight_metrics": "metric",
    "show_stats": "metric",
    "show_summary_card": "card",
    "render_hash_ring": "ring_init",
    "display_formula": "calc_show_formula",
    "render_data_structure": "reveal_graph",
}

STAGE_TARGETS = {"", "stage_canvas", "canvas", "stage", "root"}
KNOWN_NODES = {"client", "lb", "web", "redis", "mysql", "mq", "worker", "single"}
NODE_ALIASES = {
    "web_nodes": "web",
    "mysql_primary": "mysql",
    "single_box": "single",
    "server": "single",
    "user": "client",
    "cache": "redis",
    "caching_layer": "redis",
    "cdn": "lb",
    "load_balancer": "lb",
    "master": "mysql",
    "slave": "mysql",
}


def _merge_params(act: dict) -> dict:
    out = dict(act)
    params = out.pop("params", None)
    if isinstance(params, dict):
        for k, v in params.items():
            out.setdefault(k, v)
    return out


def _is_css_target(target: object) -> bool:
    s = str(target or "")
    return s.startswith("#") or s.startswith(".")


def normalize_action(act: object, scene: dict | None = None, index: int = 1) -> dict | None:
    scene = scene or {}
    if isinstance(act, str):
        act = {"type": act}
    if not isinstance(act, dict):
        return None
    out = _merge_params(act)
    raw_type = out.get("type")
    if not raw_type:
        if scene.get("graph"):
            out["type"] = "reveal_graph"
        else:
            out["type"] = "enter"
            out.setdefault("target", "#title")
        raw_type = out["type"]
    t = str(raw_type)

    if t not in PLAYER_TYPES:
        mapped = TYPE_ALIASES.get(t)
        if not mapped:
            low = t.lower()
            if "ring" in low:
                mapped = "ring_init"
            elif "formula" in low or "calc" in low:
                mapped = "calc_show_formula"
            elif "packet" in low or "flow" in low:
                mapped = "packet"
            elif "highlight" in low or "summary" in low or "card" in low:
                mapped = "card"
            elif scene.get("graph") or scene.get("ring") or scene.get("array"):
                mapped = "reveal_graph"
            else:
                mapped = "enter"
        out["source_type"] = t
        out["type"] = mapped
        t = mapped

    target = out.get("target") or out.get("id")
    if isinstance(target, str) and target in NODE_ALIASES:
        target = NODE_ALIASES[target]
        out["target"] = target
    if t == "enter":
        if not target or str(target) in STAGE_TARGETS or not _is_css_target(target):
            if str(target) not in STAGE_TARGETS and target and scene.get("graph"):
                out["type"] = "add_node" if str(target) in KNOWN_NODES else "reveal_graph"
                out["target"] = target
            else:
                out["target"] = "#title"
    elif t == "add_node":
        if not target or str(target) in STAGE_TARGETS or str(target) not in KNOWN_NODES:
            out["type"] = "reveal_graph"
    elif t in ("highlight", "focus", "node"):
        if str(target or "") not in KNOWN_NODES:
            out["type"] = "reveal_graph"
    elif t in ("connect", "packet"):
        fr, to = out.get("from"), out.get("to")
        if fr in NODE_ALIASES:
            out["from"] = NODE_ALIASES[fr]; fr = out["from"]
        if to in NODE_ALIASES:
            out["to"] = NODE_ALIASES[to]; to = out["to"]
        if fr not in KNOWN_NODES or to not in KNOWN_NODES:
            out["type"] = "reveal_graph"
    elif t == "packet":
        if not (out.get("from") and out.get("to")):
            out["type"] = "reveal_graph" if scene.get("graph") else "enter"
            if out["type"] == "enter":
                out.setdefault("target", "#title")
    elif t == "card":
        out.setdefault("index", index)
    elif t == "metric":
        out.setdefault("target", "cpu")
        out.setdefault("value", 80)
    return out


def normalize_scene_actions(scene: dict) -> list[dict]:
    raw = scene.get("actions") or []
    out: list[dict] = []
    for i, act in enumerate(raw, 1):
        n = normalize_action(act, scene, i)
        if n:
            out.append(n)
    scene["actions"] = out
    return out
