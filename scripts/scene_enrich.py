"""Dynamically clean copy, localize titles, and fill graph/actions for any scene."""
from __future__ import annotations

import re
from pathlib import Path

from scripts.action_normalize import PLAYER_TYPES, normalize_scene_actions

ROOT = Path(__file__).resolve().parent.parent

GLOSSARY = {
    "single-server-setup": "单机部署",
    "single_server_setup": "单机部署",
    "Single Server Setup": "单机部署",
    "single server": "单机服务器",
    "Single Server": "单机服务器",
    "Database Separation": "数据库分离",
    "Load Balancer": "负载均衡",
    "Vertical Scaling": "垂直扩展",
    "Horizontal Scaling": "水平扩展",
    "Database Replication": "数据库复制",
    "Content Delivery Network": "内容分发网络",
    "Request Flow": "请求路径",
    "web app": "Web 应用",
    "database": "数据库",
    "cache": "缓存",
    "Section ": "第",
}

STAGE_TOPOLOGIES = [
    ({"single-server", "single_server", "单机部署", "单机架构", "单机服务器", "单机"}, {
        "nodes": ["client", "single"],
        "edges": [["client", "single", "blue"]],
    }),
    ({"database-separation", "db-separation", "数据库分离", "拆分数据库", "独立主机", "拆库"}, {
        "nodes": ["client", "web", "mysql"],
        "edges": [["client", "web", "blue"], ["web", "mysql", "blue"]],
    }),
    ({"load-balancer", "load_balancer", "lb", "负载均衡", "流量分发"}, {
        "nodes": ["client", "lb", "web", "mysql"],
        "edges": [["client", "lb", "blue"], ["lb", "web", "blue"], ["web", "mysql", "blue"]],
    }),
    ({"database-replication", "replication", "主从复制", "主从架构", "主从", "读写分离"}, {
        "nodes": ["client", "lb", "web", "mysql"],
        "edges": [["client", "lb", "blue"], ["lb", "web", "blue"], ["web", "mysql", "blue"]],
    }),
    ({"caching", "cache", "redis", "缓存层", "多级缓存", "缓存"}, {
        "nodes": ["client", "web", "redis", "mysql"],
        "edges": [["client", "web", "blue"], ["web", "redis", "blue"], ["web", "mysql", "blue"]],
    }),
    ({"cdn", "content-delivery", "静态资源", "边缘加速", "内容分发"}, {
        "nodes": ["client", "lb", "web", "redis", "mysql"],
        "edges": [["client", "lb", "blue"], ["lb", "web", "blue"], ["web", "redis", "blue"], ["web", "mysql", "blue"]],
    }),
    ({"message-queue", "queue", "mq", "消息队列", "异步削峰", "worker"}, {
        "nodes": ["web", "mq", "worker", "mysql"],
        "edges": [["web", "mq", "blue"], ["mq", "worker", "blue"], ["worker", "mysql", "blue"]],
    }),
]

HTML_RE = re.compile(r"<[^>]+>", re.S)
MD_IMG_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
LATIN_RE = re.compile(r"[A-Za-z]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def clean_text(text: object) -> str:
    s = str(text or "")
    s = HTML_RE.sub(" ", s)
    s = MD_IMG_RE.sub(" ", s)
    s = MD_LINK_RE.sub(r"\1", s)
    s = re.sub(r"[#*_`>]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def localize_text(text: str) -> str:
    s = clean_text(text)
    for en, zh in sorted(GLOSSARY.items(), key=lambda kv: -len(kv[0])):
        s = re.sub(re.escape(en), zh, s, flags=re.I)
    if not s:
        return s
    latin = len(LATIN_RE.findall(s))
    cjk = len(CJK_RE.findall(s))
    if latin > 12 and cjk == 0:
        return ""
    if cjk:
        parts = [p.strip() for p in re.split(r"(?<=[。！？；])", s) if p.strip()]
        keep = [p for p in parts if CJK_RE.search(p)]
        if keep:
            return "".join(keep)
    return s


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[。！？；\n]+", clean_text(text)) if p.strip()]
    return [p for p in parts if p and CJK_RE.search(p)]


def infer_graph(text: str) -> dict:
    blob = (text or "").lower()
    for keys, graph in STAGE_TOPOLOGIES:
        for k in keys:
            if k.lower() in blob:
                return graph
    return {"nodes": ["client", "single"], "edges": [["client", "single", "blue"]]}

def default_actions(scene: dict) -> list[dict]:
    stype = scene.get("scene_type") or "evolve"
    graph = scene.get("graph") or {}
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    acts: list[dict] = []
    t = 0.45
    if stype in ("problem", "evolve", "flow") and nodes:
        for n in nodes:
            acts.append({"type": "add_node", "target": n, "at": round(t, 2)})
            t += 0.45
        for e in edges:
            if isinstance(e, (list, tuple)) and len(e) >= 2:
                acts.append({"type": "connect", "from": e[0], "to": e[1], "at": round(t, 2)})
                t += 0.4
                acts.append({
                    "type": "packet",
                    "from": e[0],
                    "to": e[1],
                    "color": e[2] if len(e) > 2 else "blue",
                    "at": round(t, 2),
                })
                t += 0.7
        if stype == "problem":
            acts.append({"type": "metric", "target": "cpu", "value": 90, "at": round(t, 2)})
            acts.append({"type": "metric", "target": "io", "value": 75, "at": round(t + 0.5, 2)})
            acts.append({"type": "alert", "at": round(t + 1.0, 2)})
        elif nodes:
            acts.append({"type": "focus", "target": nodes[-1], "at": round(t, 2)})
    elif stype == "summary":
        cards = scene.get("cards") or []
        for i in range(1, max(4, len(cards) + 1)):
            title_text = cards[i - 1].get("title", "") if i <= len(cards) else f"要点 {i}"
            acts.append({"type": "card", "index": i, "title": title_text, "at": round(0.6 + (i - 1) * 1.2, 2)})
    elif stype == "hash_ring":
        acts.append({"type": "ring_init", "at": 0.4})
        acts.append({"type": "ring_route", "angle": 45, "at": 1.4})
    elif stype in ("hook", "preview"):
        acts.append({"type": "enter", "target": "#title", "at": 0.2})
    return acts


def _actions_playable(scene: dict) -> bool:
    acts = scene.get("actions") or []
    playable = [a for a in acts if isinstance(a, dict) and a.get("type") in PLAYER_TYPES]
    return len(playable) > 0


def generate_summary_cards(src_sents: list[str], title: str) -> list[dict]:
    """Generate 3 clear, distinct takeaway cards for summary scene."""
    classes = ["active", "success", "warning"]
    fallbacks = [
        {"title": "1. 核心架构认知", "desc": "明确基础组件分工与数据流动路径", "cls": "active"},
        {"title": "2. 瓶颈与单点风险", "desc": "资源争抢、物理上限与故障影响面", "cls": "warning"},
        {"title": "3. 演进破局方向", "desc": "状态解耦、独立扩容与高可用保障", "cls": "success"},
    ]
    if not src_sents:
        return fallbacks
    cards = []
    for idx, s in enumerate(src_sents[:3]):
        parts = [p.strip() for p in re.split(r"[，,：:]", s) if p.strip()]
        head = parts[0] if parts else f"核心要点 {idx+1}"
        desc = "，".join(parts[1:]) if len(parts) > 1 else s
        cards.append({
            "title": f"{idx+1}. {head[:16]}",
            "desc": desc[:36],
            "cls": classes[idx % len(classes)],
        })
    while len(cards) < 3:
        cards.append(fallbacks[len(cards)])
    return cards[:3]


def enrich_scenes(
    scenes: list[dict],
    *,
    source_text: str = "",
    next_title: str = "",
    badge_prefix: str = "",
    topic_hint: str = "",
) -> list[dict]:
    """Reorder and enrich scenes: hook -> problem -> flow/evolve -> summary -> preview."""
    # 1. Separate by role to guarantee strict order: summary BEFORE preview
    hooks = [s for s in scenes if s.get("scene_type") == "hook"]
    problems = [s for s in scenes if s.get("scene_type") == "problem"]
    body = [s for s in scenes if s.get("scene_type") not in ("hook", "problem", "summary", "preview")]
    summaries = [s for s in scenes if s.get("scene_type") == "summary"]
    previews = [s for s in scenes if s.get("scene_type") == "preview"]

    # If missing summary or preview, create stubs
    if not summaries:
        summaries = [{"scene_type": "summary", "title": "本节要点", "actions": []}]
    if not previews:
        previews = [{"scene_type": "preview", "title": f"下一节：{next_title or '后续演进'}", "actions": []}]

    reordered = hooks + problems + body + summaries + previews

    src_sents = split_sentences(source_text)
    next_t_clean = localize_text(next_title).strip("：: ") or "后续演进"

    enriched: list[dict] = []
    for idx, scene in enumerate(reordered, 1):
        stype = scene.get("scene_type") or "evolve"
        sid = f"{idx:02d}"
        scene["scene"] = sid
        scene["id"] = scene.get("id") or f"shot_{sid}"

        title = localize_text(str(scene.get("title") or scene.get("title_zh") or ""))
        narration = localize_text(str(scene.get("narration") or ""))

        if stype == "hook":
            if not title:
                title = "一切从基础架构开始"
            if not narration:
                if src_sents:
                    narration = f"这一节我们来探讨：{src_sents[0]}。"
                else:
                    narration = "这一节我们从基础部署出发，看看系统架构的核心考点与演进脉络。"
            scene.setdefault("takeaway", narration.split("。")[0] + "。")
            scene.setdefault("badge", badge_prefix or "核心认知")

        elif stype == "problem":
            if not title:
                title = "请求链路与单点瓶颈"
            if not narration:
                if len(src_sents) >= 2:
                    narration = f"首先理清请求路径：{src_sents[1]}。当并发上升时，硬件资源迅速见顶，单点故障直接影响全站。"
                else:
                    narration = "用户请求直达服务器，Web 与数据层共享资源，流量突增时极易成为整个系统的单点瓶颈。"
            scene.setdefault("badge", "请求链路")

        elif stype == "summary":
            title = "本节核心要点"
            scene["title"] = title
            scene["badge"] = "本节要点"
            cards = scene.get("cards") or []
            if not cards or not any(c.get("title") for c in cards):
                cards = generate_summary_cards(src_sents, title)
            scene["cards"] = cards
            # Dynamic narration summarizing the cards
            card_summaries = [c.get("desc") or c.get("title") for c in cards[:3]]
            narration = f"总结本节三要点：第一，{card_summaries[0]}；第二，{card_summaries[1]}；第三，{card_summaries[2]}。"

        elif stype == "preview":
            title = f"下一节：{next_t_clean}"
            scene["title"] = title
            scene["badge"] = "下一节预告"
            scene["next_title"] = next_t_clean
            scene["teasers"] = [
                f"{next_t_clean} 核心拆解",
                "独立扩展与高可用架构",
                "大厂面试核心考点推演",
            ]
            scene["cta"] = "关注主播 · 追更系统设计全书"
            narration = f"掌握了本节核心，下一节我们继续拆解：{next_t_clean}。关注主播，下期不见不散！"

        else:
            if not title:
                title = "关键权衡与架构演进"
            if not narration:
                if len(src_sents) >= 3:
                    narration = f"在架构选型中需要权衡：{src_sents[2]}。理解这些取舍，才能明确下一步演进方向。"
                else:
                    narration = "系统的每一次演进都是在容量、延迟与复杂度之间做权衡，必须针对痛点精准解耦。"
            scene.setdefault("badge", "关键权衡")

        scene["title"] = title
        scene["title_zh"] = title
        scene["narration"] = narration

        # Keywords
        kws = scene.get("keywords") or []
        scene["keywords"] = [localize_text(str(k)) or str(k) for k in kws][:3]
        if not scene["keywords"] and src_sents:
            scene["keywords"] = [w for w in re.findall(r"[\u4e00-\u9fff]{2,6}", narration)[:3]]

        # Graph inference
        if stype in ("problem", "evolve", "flow") and not (scene.get("graph") or {}).get("nodes"):
            scene["graph"] = infer_graph(" ".join([topic_hint, title, narration, source_text]))

        # Normalize and fallback actions
        normalize_scene_actions(scene)
        if not _actions_playable(scene):
            scene["actions"] = default_actions(scene)
            normalize_scene_actions(scene)

        enriched.append(scene)

    return enriched


def enrich_scene(
    scene: dict,
    *,
    source_text: str = "",
    next_title: str = "",
    badge_prefix: str = "",
    topic_hint: str = "",
) -> dict:
    return enrich_scenes([scene], source_text=source_text, next_title=next_title, badge_prefix=badge_prefix, topic_hint=topic_hint)[0]
