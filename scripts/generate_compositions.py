#!/usr/bin/env python3
"""Generate HyperFrames HTML from Scene JSON + ArchGraph + CalcBoard + AlgoViz + action-player."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPS_DIR = ROOT / "compositions"
_ACTIVE_THEME: dict = {}


def _html_header(theme: dict | None = None) -> str:
    t = theme or _ACTIVE_THEME or {}
    primary = t.get("primary_color") or "#3B82F6"
    glow = t.get("primary_glow") or "rgba(59, 130, 246, 0.25)"
    bg = t.get("bg_color") or "#0B0F19"
    style = f"""
  <style id="course-theme">
    :root {{
      --color-primary: {primary};
      --color-primary-glow: {glow};
      --bg-primary: {bg};
      --border-active: {primary};
      --bg-card-active: {glow};
    }}
  </style>"""
    return f"""<!doctype html>
<html lang="zh-CN" data-resolution="portrait">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <link rel="stylesheet" href="assets/styles/global.css" />
{style}
  <script src="assets/scripts/gsap.min.js"></script>
  <script src="assets/scripts/motion.js"></script>
  <script src="assets/scripts/arch-graph.js"></script>
  <script src="assets/scripts/calc-board.js"></script>
  <script src="assets/scripts/algo-viz.js"></script>
  <script src="assets/scripts/action-player.js"></script>
</head>
<body>
"""


HTML_HEADER = _html_header()

HTML_FOOTER = """
</body>
</html>
"""

CODE_LINES = [
    "get(key):",
    "  v = redis.get(key)",
    "  if v: return v          # HIT",
    "  v = db.query(key)       # MISS",
    "  redis.set(key, v)",
    "  return v",
]


def _wrap(scene: dict, duration: float, inner: str, extra_js: str = "") -> str:
    scene_id = scene.get("scene") or "01"
    actions = list(scene.get("actions") or [])
    prelude = [
        {"type": "enter", "target": "#badge", "at": 0.05},
        {"type": "enter", "target": "#title", "at": 0.2},
    ]
    if scene.get("keywords"):
        prelude.append({"type": "enter", "target": ".keyword-legend", "at": 0.35})
    if scene.get("graph"):
        prelude.append({
            "type": "reveal_graph",
            "at": 0.0 if scene.get("graph_hold") else 0.45,
            "instant": bool(scene.get("graph_hold")),
        })
    if scene.get("code"):
        prelude.append({"type": "enter", "target": "#code-panel", "at": 2.0})
    if scene.get("terminal"):
        prelude.append({"type": "enter", "target": "#term-panel", "at": 1.6})
    if scene.get("calc_board"):
        prelude.append({"type": "calc_show_formula", "at": 0.35})

    def _v(k: str):
        return scene[k] if k in scene and scene[k] is not None else None

    payload_dict = {
        "actions": prelude + actions,
        "graph": scene.get("graph") or {},
        "calc_board": _v("calc_board"),
        "assumptions": _v("assumptions"),
        "ladder": _v("ladder"),
        "ring": _v("ring") if _v("ring") is not None else ({} if scene.get("scene_type") == "hash_ring" else None),
        "bucket": _v("bucket") if _v("bucket") is not None else ({} if scene.get("scene_type") == "token_bucket" else None),
        "sliding_window": _v("sliding_window") if _v("sliding_window") is not None else ({} if scene.get("scene_type") == "sliding_window" else None),
        "array": _v("array"),
        "linked_list": _v("linked_list"),
        "hash_map": _v("hash_map"),
        "tree": _v("tree"),
        "stack": _v("stack"),
        "dp_table": _v("dp_table"),
    }
    payload = json.dumps(payload_dict, ensure_ascii=False)

    return f"""{_html_header(scene.get("theme") or _ACTIVE_THEME)}
  <div id="root" class="composition-root" data-composition-id="shot_{scene_id}" data-mood="{scene.get("mood") or (scene.get("avatar") or {}).get("mood") or "normal"}" data-start="0" data-duration="{duration}" data-width="1080" data-height="1920">
    <div class="bg-ambient"></div>
    <div class="bg-grid"></div>
    {inner}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    const SCENE = {payload};
    if (SCENE.graph && SCENE.graph.nodes) {{
      ArchGraph.mount("#topo", SCENE.graph);
    }}
    if (SCENE.calc_board) {{
      CalcBoard.mount("#calc-board-mount", SCENE.calc_board);
    }}
    if (SCENE.assumptions) {{
      CalcBoard.mountAssumptions("#assumptions-mount", SCENE.assumptions);
    }}
    if (SCENE.ladder) {{
      CalcBoard.mountUnitsLadder("#ladder-mount", SCENE.ladder);
    }}
    if (SCENE.ring) {{
      AlgoViz.mountRing("#ring-mount", SCENE.ring);
    }}
    if (SCENE.bucket) {{
      AlgoViz.mountBucket("#bucket-mount", SCENE.bucket);
    }}
    if (SCENE.sliding_window) {{
      AlgoViz.mountSlidingWindow("#window-mount", SCENE.sliding_window);
    }}
    const algoEl = document.querySelector("#algo-mount");
    if (algoEl && window.AlgoViz) {{
      if (SCENE.array) AlgoViz.mountArray("#algo-mount", SCENE.array);
      else if (SCENE.linked_list) AlgoViz.mountLinkedList("#algo-mount", SCENE.linked_list);
      else if (SCENE.hash_map) AlgoViz.mountHashMap("#algo-mount", SCENE.hash_map);
      else if (SCENE.tree) AlgoViz.mountTree("#algo-mount", SCENE.tree);
      else if (SCENE.stack) AlgoViz.mountStack("#algo-mount", SCENE.stack);
      else if (SCENE.dp_table) AlgoViz.mountDpTable("#algo-mount", SCENE.dp_table);
      else if (SCENE.ring) AlgoViz.mountRing("#algo-mount", SCENE.ring);
      else if (SCENE.bucket) AlgoViz.mountBucket("#algo-mount", SCENE.bucket);
      else if (SCENE.sliding_window) AlgoViz.mountSlidingWindow("#algo-mount", SCENE.sliding_window);
    }}
    if (SCENE.linked_list && SCENE.hash_map && document.querySelector("#hm-mount")) {{
      AlgoViz.mountHashMap("#hm-mount", SCENE.hash_map);
    }}
    const tl = gsap.timeline({{ paused: true }});
    {extra_js}
    playActions(tl, SCENE.actions, 0.55);
    window.__timelines["shot_{scene_id}"] = tl;
  </script>
{HTML_FOOTER}"""


def _header(scene: dict) -> str:
    kw = scene.get("keywords") or []
    kw_html = ""
    if kw:
        items = "".join(f'<span class="legend-item legend-{i % 3}">{k}</span>' for i, k in enumerate(kw[:3]))
        kw_html = f'\n      <div class="keyword-legend">{items}</div>'
    return f'''
    <div class="zone-header">
      <div id="badge" class="chapter-badge">{scene.get("badge", "")}</div>
      <h1 id="title" class="slide-title">{scene.get("title", "")}</h1>{kw_html}
    </div>'''


def generate_cover_composition(scene: dict, duration: float) -> str:
    inner = f'''
    <div class="zone-header" style="padding-top:260px;">
      <div class="chapter-badge">{scene.get("badge", "系统设计课程")}</div>
      <h1 id="title" class="slide-title" style="font-size:64px;line-height:1.2;">{scene.get("title", "")}</h1>
    </div>
    <div class="zone-content" style="display:flex;align-items:center;justify-content:center;">
      <div id="cover-box" class="beat-card" style="text-align:center;padding:48px 36px;">
        <div style="font-size:34px;color:#93c5fd;line-height:1.5;">{scene.get("subtitle", "")}</div>
        <div style="font-size:28px;color:var(--color-secondary);margin-top:28px;line-height:1.6;">{scene.get("opening", "")}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#cover-box"), 0.45);\n'
    return _wrap(scene, duration, inner, extra)


def generate_hook_composition(scene: dict, duration: float):
    actions = scene.get("actions") or []
    counter_act = next((a for a in actions if a.get("type") == "counter"), None)
    if not counter_act:
        takeaway = scene.get("narration") or scene.get("title") or ""
        inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="hook-card" class="beat-card active" style="padding:48px 36px;text-align:center;">
        <div style="font-size:32px;line-height:1.6;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
        extra = 'tl.add(motion.enter("#hook-card"), 0.4);\n'
        return _wrap(scene, duration, inner, extra)
    from_val = counter_act.get("from", 100)
    to_val = counter_act.get("to", 10000)
    alert_act = next((a for a in actions if a.get("type") == "alert"), None)
    alert_msg = alert_act.get("message", "SERVER OVERLOAD") if alert_act else "SERVER OVERLOAD"
    metric_label_zh = scene.get("metric_label_zh") or "并发在线用户"
    metric_label_en = scene.get("metric_label_en") or "ONLINE USERS"
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div class="svg-canvas-container" id="diagram-wrap" style="display:flex;align-items:center;justify-content:center;">
        <div id="counter-box" class="beat-card" style="text-align:center;padding:40px 60px;">
          <div class="metric-label" style="justify-content:center;gap:16px;margin-bottom:16px;"><span>{metric_label_zh}</span><span>{metric_label_en}</span></div>
          <div style="display:flex;align-items:baseline;justify-content:center;gap:20px;">
            <span style="font-size:64px;font-weight:800;color:#60A5FA;font-family:var(--font-mono);">{from_val:,}</span>
            <span style="font-size:44px;color:#94A3B8;font-weight:700;">→</span>
            <span id="counter" style="font-size:80px;font-weight:800;color:#EF4444;font-family:var(--font-mono);">{from_val:,}</span>
          </div>
        </div>
      </div>
      <div id="alert-box" class="beat-card danger" style="opacity:0;">
        <div style="font-size:32px;font-weight:700;color:#FCA5A5;text-align:center;">⚠️ {alert_msg}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#counter-box"), 0.4);\n'
    return _wrap(scene, duration, inner, extra)


def generate_problem_composition(scene: dict, duration: float) -> str:
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div class="svg-canvas-container" id="diagram-wrap">
        <svg class="svg-canvas" viewBox="0 0 936 560" id="topo"></svg>
      </div>
      <div id="metrics" class="metric-container">
        <div class="metric-row">
          <div class="metric-label"><span>CPU</span><span id="cpu-val">0%</span></div>
          <div class="metric-bar-bg"><div id="cpu-bar" class="metric-bar-fill"></div></div>
        </div>
        <div class="metric-row">
          <div class="metric-label"><span>磁盘 IO</span><span id="io-val">0%</span></div>
          <div class="metric-bar-bg"><div id="io-bar" class="metric-bar-fill"></div></div>
        </div>
      </div>
    </div>'''
    return _wrap(scene, duration, inner, "")


def generate_graph_composition(scene: dict, duration: float, with_code: bool = False) -> str:
    code_html = ""
    lines = scene.get("code_lines") or CODE_LINES
    if with_code or scene.get("code"):
        rows = []
        for i, line in enumerate(lines):
            rows.append(
                f'<div class="code-line" id="code-line-{i}"><span class="code-lineno">{i+1}</span> {line}</div>'
            )
        code_html = f'''
      <div id="code-panel" class="code-panel">
        <div class="window-header mini">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">Cache Aside 伪代码</div>
          <div class="window-badge">REDIS</div>
        </div>
        <div class="code-body">{"".join(rows)}</div>
      </div>'''
    term_html = ""
    if scene.get("terminal"):
        trows = []
        for i, line in enumerate(scene.get("terminal") or []):
            trows.append(f'<div class="term-line" id="term-line-{i}" style="opacity:0;">{line}</div>')
        term_html = f'''
      <div id="term-panel" class="term-panel">
        <div class="window-header mini">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">Terminal Output</div>
          <div class="window-badge">BASH</div>
        </div>
        <div class="term-body">{"".join(trows)}</div>
      </div>'''
    takeaway = scene.get("narration", "")
    has_sub = with_code or bool(scene.get("code")) or bool(scene.get("terminal"))
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div class="svg-canvas-container" id="diagram-wrap" style="height:{'520px' if has_sub else '820px'};">
        <svg class="svg-canvas" viewBox="0 0 936 560" id="topo"></svg>
      </div>
      {code_html}
      {term_html}
      <div id="takeaway" class="beat-card active">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.4);\n'
    return _wrap(scene, duration, inner, extra)


def generate_code_composition(scene: dict, duration: float) -> str:
    lines = scene.get("code_lines") or CODE_LINES
    filename = scene.get("filename") or "cache_aside.py"
    rows = []
    for i, line in enumerate(lines):
        rows.append(
            f'<div class="code-line" id="code-line-{i}"><span class="code-lineno">{i+1:2d}</span> {line}</div>'
        )
    code_body = "".join(rows)
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="code-window" class="code-window">
        <div class="window-header">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">{filename}</div>
          <div class="window-badge">PYTHON</div>
        </div>
        <div id="code-panel" class="code-panel-body">
          {code_body}
        </div>
      </div>
      <div id="takeaway" class="beat-card active">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#code-window"), 0.4);\ntl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_terminal_composition(scene: dict, duration: float) -> str:
    term_lines = scene.get("terminal") or [
        "$ curl -i https://api.service.com/users/10001",
        "HTTP/2 200 OK",
        "content-type: application/json",
        "x-cache-status: HIT (Redis: 1.2ms)",
        '{"id":10001,"status":"active","cached":true}',
    ]
    trows = []
    for i, line in enumerate(term_lines):
        trows.append(f'<div class="term-line" id="term-line-{i}" style="opacity:0;">{line}</div>')
    term_body = "".join(trows)
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="term-window" class="terminal-window">
        <div class="window-header">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">bash — 80x24</div>
          <div class="window-badge">BASH</div>
        </div>
        <div id="term-panel" class="term-panel-body">
          {term_body}
        </div>
      </div>
      <div id="takeaway" class="beat-card active">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#term-window"), 0.4);\ntl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_summary_composition(scene: dict, duration: float) -> str:
    cards = list(scene.get("cards") or [])
    if not cards:
        for a in scene.get("actions") or []:
            if a.get("type") == "card":
                title_raw = a.get("title", "")
                if ":" in title_raw:
                    t, d = title_raw.split(":", 1)
                    cards.append({"title": t.strip(), "desc": d.strip()})
                elif "：" in title_raw:
                    t, d = title_raw.split("：", 1)
                    cards.append({"title": t.strip(), "desc": d.strip()})
                else:
                    cards.append({"title": title_raw.strip(), "desc": ""})
    if not cards:
        cards = [
            {"title": "1. 核心架构设计", "desc": "系统设计原则与最佳实践", "cls": "active"},
            {"title": "2. 高性能与可扩展", "desc": "状态外置与多级缓存优化", "cls": "success"},
            {"title": "3. 高可用与容灾", "desc": "熔断限流与异步削峰填谷", "cls": "warning"},
        ]
    classes = ["active", "success", "warning"]
    card_html = []
    for i, c in enumerate(cards[:3], 1):
        cls = c.get("cls") or classes[(i - 1) % len(classes)]
        card_html.append(
            f'<div id="rule{i}" class="beat-card {cls}" style="opacity:0;">'
            f'<div style="font-size:32px;font-weight:700;">{c.get("title","")}</div>'
            f'<div style="font-size:26px;color:var(--color-secondary);margin-top:8px;">{c.get("desc","")}</div>'
            f"</div>"
        )
    cta_text = scene.get("cta") or "👉 下一集：深入拆解系统设计实战"
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      {"".join(card_html)}
      <div id="cta-box" class="beat-card" style="opacity:0;border-style:dashed;">
        <div style="font-size:28px;font-weight:700;color:#93c5fd;">{cta_text}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#cta-box"), 4.4);\n'
    return _wrap(scene, duration, inner, extra)


# =========================================================================
# Template B: Estimation Compositions (CalcStep, Assumptions, UnitsLadder)
# =========================================================================

def generate_calc_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="calc-board-mount"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_assumptions_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="assumptions-mount"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.4);\n'
    return _wrap(scene, duration, inner, extra)


def generate_units_ladder_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="ladder-mount"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.4);\n'
    return _wrap(scene, duration, inner, extra)


# =========================================================================
# Template C: Algorithm Compositions (Ring, TokenBucket, SlidingWindow, Naive)
# =========================================================================

def generate_algo_ring_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div class="svg-canvas-container" id="ring-mount" style="height:620px;"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_token_bucket_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="bucket-mount"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_sliding_window_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="window-mount"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_naive_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    problem_text = scene.get("problem_text") or "朴素算法存在单点崩溃或全量数据倾斜风险"
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      <div id="naive-box" class="beat-card danger" style="padding:48px 36px;text-align:center;">
        <div style="font-size:36px;font-weight:800;color:#F87171;margin-bottom:16px;">⚠️ 朴素算法瓶颈 (Naive Bottleneck)</div>
        <div style="font-size:28px;color:#FCA5A5;line-height:1.6;">{problem_text}</div>
      </div>
      <div id="takeaway" class="beat-card active" style="opacity:0;margin-top:24px;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#naive-box"), 0.4);\ntl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_algo_mount_composition(scene: dict, duration: float) -> str:
    takeaway = scene.get("narration", "")
    hm = ""
    if scene.get("linked_list") and scene.get("hash_map"):
        hm = '<div id="hm-mount" class="algo-split-map"></div>'
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      {hm}
      <div class="svg-canvas-container{' algo-split-list' if hm else ''}" id="algo-mount" style="height:{'380px' if hm else '620px'};"></div>
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#takeaway"), 1.2);\n'
    return _wrap(scene, duration, inner, extra)


def generate_algo_viz_composition(scene: dict, duration: float) -> str:
    """Fallback viz when algo_viz/edge_case has no ring/bucket/window/graph."""
    takeaway = scene.get("narration") or ""
    steps = scene.get("steps") or scene.get("viz_steps") or []
    if not steps:
        title = scene.get("title") or "算法步骤"
        steps = [
            {"label": "1", "text": title},
            {"label": "2", "text": takeaway[:36] + ("…" if len(takeaway) > 36 else "")},
        ]
    cards = []
    classes = ["active", "success", "warning"]
    for i, step in enumerate(steps[:4], 1):
        if isinstance(step, str):
            label, text = str(i), step
        else:
            label = str(step.get("label") or i)
            text = step.get("text") or step.get("title") or ""
        cls = classes[(i - 1) % len(classes)]
        cards.append(
            f'<div id="viz{i}" class="beat-card {cls}" style="opacity:0;padding:22px 28px;margin-bottom:16px;">'
            f'<div style="font-size:28px;font-weight:800;margin-bottom:8px;">{label}</div>'
            f'<div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{text}</div>'
            f"</div>"
        )
    extra_parts = [f'tl.add(motion.enter("#viz{i}"), {0.35 + i * 0.55:.2f});' for i in range(1, min(len(steps), 4) + 1)]
    extra_parts.append('tl.add(motion.enter("#takeaway"), 1.6);')
    inner = f'''
    {_header(scene)}
    <div class="zone-content">
      {"".join(cards)}
      <div id="takeaway" class="beat-card active" style="opacity:0;">
        <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">{takeaway}</div>
      </div>
    </div>'''
    return _wrap(scene, duration, inner, "\n".join(extra_parts) + "\n")


def generate_preview_composition(scene: dict, duration: float) -> str:
    next_title = scene.get("next_title") or scene.get("title", "下集预告")
    badge_text = scene.get("badge") or "下集预告 · NEXT EPISODE"
    teasers = scene.get("teasers") or [
        "核心架构机制与实战演进",
        "高并发与高可用技术避坑指南",
        "工业级系统设计标准推演",
    ]
    teaser_html = []
    classes = ["active", "success", "warning"]
    for i, t in enumerate(teasers[:3], 1):
        cls = classes[(i - 1) % len(classes)]
        teaser_html.append(
            f'<div id="teaser{i}" class="beat-card {cls}" style="opacity:0;padding:18px 24px;margin-bottom:14px;">'
            f'<div style="font-size:26px;font-weight:700;">✨ 核心看点 {i}：{t}</div>'
            f'</div>'
        )
    cta_text = scene.get("cta") or "🔔 关注主播 · 追更《系统设计面试通关课》"
    inner = f'''
    <div class="zone-header" style="padding-top:140px;">
      <div id="badge" class="chapter-badge" style="border-color:#F59E0B;color:#FCD34D;background:rgba(245,158,11,0.15);">{badge_text}</div>
      <h1 id="title" class="slide-title" style="font-size:52px;line-height:1.25;">{next_title}</h1>
    </div>
    <div class="zone-content">
      <div id="preview-box" class="beat-card" style="opacity:0;margin-bottom:18px;border-color:rgba(59,130,246,0.5);">
        <div style="font-size:24px;color:#93C5FD;font-weight:700;margin-bottom:14px;">🔥 下期精彩内容划重点：</div>
        {"".join(teaser_html)}
      </div>
      <div id="cta-box" class="beat-card" style="opacity:0;border:2px dashed #38BDF8;background:rgba(14,165,233,0.12);text-align:center;padding:22px 20px;">
        <div style="font-size:30px;font-weight:800;color:#38BDF8;">{cta_text}</div>
      </div>
    </div>'''
    extra = 'tl.add(motion.enter("#preview-box"), 0.4);\ntl.add(motion.enter("#teaser1"), 0.8);\ntl.add(motion.enter("#teaser2"), 1.6);\ntl.add(motion.enter("#teaser3"), 2.4);\ntl.add(motion.enter("#cta-box"), 3.2);\ntl.add(motion.pulse("#cta-box", { scale: 1.05, repeat: 2 }), 3.8);\n'
    return _wrap(scene, duration, inner, extra)

def generate_all_compositions(timed_spec_file: Path) -> list[Path]:
    global _ACTIVE_THEME
    spec = json.loads(timed_spec_file.read_text(encoding="utf-8"))
    _ACTIVE_THEME = spec.get("theme") or {}
    contract_path = spec.get("contract")
    extras: dict[str, dict] = {}
    if contract_path:
        source = Path(contract_path)
        if not source.is_absolute():
            source = ROOT / source
        if source.exists():
            for s in json.loads(source.read_text(encoding="utf-8")).get("scenes") or []:
                extras[str(s.get("scene"))] = s

    COMPS_DIR.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for raw in spec.get("scenes") or spec.get("shots") or []:
        sid = str(raw.get("scene") or raw.get("shot", "01"))
        item = {**(extras.get(sid) or {}), **raw}
        if _ACTIVE_THEME and "theme" not in item:
            item["theme"] = _ACTIVE_THEME
        for k in ("total_duration_sec", "duration_sec"):
            if k in raw:
                item[k] = raw[k]
        item_id = sid
        dur = item.get("total_duration_sec") or item.get("duration_sec", 5.0)
        target_html = COMPS_DIR / f"shot_{item_id}.html"
        stype = item.get("scene_type") or item.get("template")

        # Routing logic
        if stype == "cover" or (item_id == "00" and not stype):
            content = generate_cover_composition(item, dur)
        elif stype == "hook":
            content = generate_hook_composition(item, dur)
        elif stype == "problem":
            content = generate_problem_composition(item, dur)
        elif stype == "summary":
            content = generate_summary_composition(item, dur)
        elif stype == "preview":
            content = generate_preview_composition(item, dur)
        elif stype == "code":
            content = generate_code_composition(item, dur)
        elif stype == "terminal":
            content = generate_terminal_composition(item, dur)
        # Template B routes
        elif stype == "calc_step" or item.get("calc_board"):
            content = generate_calc_composition(item, dur)
        elif stype == "assumptions" or item.get("assumptions"):
            content = generate_assumptions_composition(item, dur)
        elif stype == "units_ladder" or stype == "rules" or item.get("ladder"):
            content = generate_units_ladder_composition(item, dur)
        # Template C routes
        elif stype == "hash_ring" or item.get("ring"):
            content = generate_algo_ring_composition(item, dur)
        elif stype == "token_bucket" or item.get("bucket"):
            content = generate_token_bucket_composition(item, dur)
        elif stype == "sliding_window" or item.get("sliding_window"):
            content = generate_sliding_window_composition(item, dur)
        elif any(item.get(k) for k in ("array", "linked_list", "hash_map", "tree", "stack", "dp_table")):
            content = generate_algo_mount_composition(item, dur)
        elif stype == "naive":
            content = generate_naive_composition(item, dur)
        elif stype in ("algo_viz", "edge_case"):
            if item.get("ring"):
                content = generate_algo_ring_composition(item, dur)
            elif item.get("bucket"):
                content = generate_token_bucket_composition(item, dur)
            elif item.get("sliding_window"):
                content = generate_sliding_window_composition(item, dur)
            elif any(item.get(k) for k in ("array", "linked_list", "hash_map", "tree", "stack", "dp_table")):
                content = generate_algo_mount_composition(item, dur)
            elif item.get("graph") and (item.get("graph") or {}).get("nodes"):
                content = generate_graph_composition(item, dur, with_code=bool(item.get("code")))
            else:
                content = generate_algo_viz_composition(item, dur)
        else:
            content = generate_graph_composition(
                item, dur, with_code=bool(item.get("code"))
            )
        target_html.write_text(content, encoding="utf-8")
        print(f"[+] Generated {target_html} (type: {stype}, duration: {dur:.2f}s)")
        generated.append(target_html)
    return generated


if __name__ == "__main__":
    generate_all_compositions(ROOT / "data" / "shots_timed.json")
