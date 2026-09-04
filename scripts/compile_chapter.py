#!/usr/bin/env python3
"""Compile chapter/short content contract into render-ready Scene JSON specification.

Responsibilities:
1. Validate topology node references against assets/scripts/arch-graph.js.
2. Validate template recipe constraints, attribution, and required fields across multiple templates (system_evolution, estimation, algorithm).
3. Provide adaptive heuristic sniffer to auto-detect template type when unassigned.
4. Support multi-course workspaces (content/courses/<course_id>/) and decouple themes/metadata via course.json.
5. Resolve semantic avatar tiers (host/support/pip) to concrete sizes/positions via config/avatar.json.
6. Auto-fill default actions (such as summary concept cards from l1_one_liner) when omitted.
7. Export clean compiled_spec.json for the frozen V2/V3/V5 render pipeline.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_known_nodes() -> tuple[set[str], dict[str, str]]:
    """Extract known SVG graph node IDs and aliases from arch-graph.js."""
    arch_js = ROOT / "assets" / "scripts" / "arch-graph.js"
    if not arch_js.exists():
        return ({"client", "lb", "web", "redis", "mysql", "mq", "worker", "single"}, {})

    code = arch_js.read_text(encoding="utf-8")
    nodes_block = re.search(r"const NODES = \{(.*?)\n  \};", code, re.DOTALL)
    nodes = set()
    if nodes_block:
        nodes = set(re.findall(r"^\s*(\w+):\s*\{", nodes_block.group(1), re.MULTILINE))

    alias_block = re.search(r"const ALIAS = \{(.*?)\n  \};", code, re.DOTALL)
    aliases = {}
    if alias_block:
        for k, v in re.findall(r'^\s*(\w+):\s*["\'](\w+)["\']', alias_block.group(1), re.MULTILINE):
            aliases[k] = v

    return nodes, aliases


def sniff_template_type(chapter_data: dict, scenes_data: dict) -> str:
    """Heuristic Sniffer: Auto-detect template type based on content structure."""
    if chapter_data.get("template"):
        return chapter_data["template"]

    scenes = scenes_data.get("scenes") or []
    for s in scenes:
        stype = s.get("scene_type", "")
        if stype in ("calc_step", "assumptions", "units_ladder") or s.get("calc_board") or s.get("assumptions") or s.get("ladder"):
            return "estimation"
        if stype in ("hash_ring", "token_bucket", "sliding_window", "algo_viz", "naive") or s.get("ring") or s.get("bucket") or s.get("sliding_window") or s.get("array") or s.get("linked_list") or s.get("hash_map") or s.get("tree") or s.get("stack") or s.get("dp_table"):
            return "algorithm"
        if stype in ("problem", "evolve", "flow") or s.get("graph"):
            return "system_evolution"

    return "system_evolution"


class ChapterCompiler:
    def __init__(self, root: Path | None = None, course_id: str | None = None):
        self.root = root or ROOT
        self.avatar_file = self.root / "config" / "avatar.json"
        self.avatar_config = load_json(self.avatar_file) if self.avatar_file.exists() else {}
        self.known_nodes, self.aliases = get_known_nodes()
        self.set_course(course_id or "demo")

    def set_course(self, course_id: str) -> None:
        """Switch or set active course workspace."""
        self.course_id = course_id
        names = [course_id]
        if course_id == "demo":
            names.append("_demo")
        self.course_dir = self.root / "content" / "courses" / names[0]
        for name in names:
            candidate = self.root / "content" / "courses" / name
            if candidate.is_dir():
                self.course_dir = candidate
                break
        
        # 1. Load course.json
        course_json_file = self.course_dir / "course.json"
        if course_json_file.exists():
            self.course_info = load_json(course_json_file)
        else:
            self.course_info = {
                "id": course_id,
                "name": course_id,
                "theme": {
                    "primary_color": "#3B82F6",
                    "primary_glow": "rgba(59, 130, 246, 0.25)",
                    "bg_color": "#0B0F19",
                    "badge_prefix": course_id
                },
                "avatar": {
                    "image": "assets/avatars/demo.png",
                    "default_tier": "support",
                    "position": "bottom_right"
                },
                "tts": {
                    "engine": "edge",
                    "speaker": "yunxi"
                }
            }

        # 2. Load catalog.json
        catalog_file = self.course_dir / "catalog.json"
        if not catalog_file.exists():
            # Fallback to root content/catalog.json for system-design
            catalog_file = self.root / "content" / "catalog.json"

        if catalog_file.exists():
            self.catalog_file = catalog_file
            self.catalog = load_json(catalog_file)
        else:
            self.catalog_file = catalog_file
            self.catalog = {"course_id": course_id, "chapters": [], "shorts": []}

    def resolve_entry(
        self,
        chapter_id: str | None = None,
        short_id: str | None = None,
        dir_path: str | Path | None = None,
    ) -> tuple[dict, Path]:
        """Resolve catalog entry and directory for chapter or short."""
        if dir_path:
            p = Path(dir_path)
            if not p.is_absolute():
                # Check relative to course dir, then relative to root
                if (self.course_dir / p).exists():
                    p = self.course_dir / p
                else:
                    p = self.root / p
            return {"id": p.name, "dir": str(p), "template": self.course_info.get("default_template", "system_evolution")}, p

        if chapter_id is not None:
            # Normalize e.g. "1" -> "01"
            cid = f"{int(chapter_id):02d}" if chapter_id.isdigit() else chapter_id
            for ch in self.catalog.get("chapters", []):
                if ch.get("id") == cid or ch.get("slug") == chapter_id or str(ch.get("id")) == str(chapter_id):
                    dir_str = ch.get("dir", "")
                    p = self._resolve_path(dir_str)
                    return ch, p

            # If not found in current course catalog, search other courses
            courses_base = self.root / "content" / "courses"
            if courses_base.exists():
                for cdir in courses_base.iterdir():
                    if cdir.is_dir() and cdir.name != self.course_id:
                        cat_f = cdir / "catalog.json"
                        if cat_f.exists():
                            try:
                                other_cat = load_json(cat_f)
                                for ch in other_cat.get("chapters", []):
                                    if ch.get("id") == cid or ch.get("slug") == chapter_id or str(ch.get("id")) == str(chapter_id):
                                        self.set_course(cdir.name)
                                        p = self._resolve_path(ch.get("dir", ""))
                                        return ch, p
                            except Exception:
                                pass

            # Also check direct chapter directory inside course
            direct_p = self.course_dir / "chapters" / chapter_id
            if direct_p.exists():
                return {"id": chapter_id, "dir": str(direct_p), "template": self.course_info.get("default_template", "system_evolution")}, direct_p
            for ch_d in (self.course_dir / "chapters").glob(f"{cid}-*"):
                if ch_d.is_dir():
                    return {"id": cid, "dir": str(ch_d), "template": self.course_info.get("default_template", "system_evolution")}, ch_d

            raise ValueError(f"Chapter '{chapter_id}' (normalized: '{cid}') not found in course '{self.course_id}' catalog ({self.catalog_file})")

        if short_id is not None:
            for sh in self.catalog.get("shorts", []):
                if sh.get("id") == short_id or sh.get("slug") == short_id:
                    dir_str = sh.get("dir", "")
                    p = self._resolve_path(dir_str)
                    return sh, p
            raise ValueError(f"Short '{short_id}' not found in course '{self.course_id}' catalog ({self.catalog_file})")

        raise ValueError("Must specify chapter_id, short_id, or dir_path")

    def _resolve_path(self, dir_str: str) -> Path:
        """Resolve a directory path string whether it's absolute, root-relative, or course-relative."""
        p = Path(dir_str)
        if p.is_absolute():
            return p
        if (self.root / p).exists():
            return self.root / p
        if (self.course_dir / p).exists():
            return self.course_dir / p
        if (self.course_dir / "chapters" / p).exists():
            return self.course_dir / "chapters" / p
        return self.root / p

    def validate(
        self,
        entry: dict,
        chapter_data: dict,
        scenes_data: dict,
        template_data: dict,
    ) -> list[str]:
        """Run strict schema, recipe, and semantic integrity checks."""
        errors: list[str] = []

        # 1. Attribution check
        attribution = chapter_data.get("attribution") or self.course_info.get("attribution")
        if not attribution:
            errors.append("chapter.json: 缺少 'attribution' 字段（可写 Demo 或课程出处）")

        # 2. Scenes check
        scenes = scenes_data.get("scenes") or []
        if not scenes:
            errors.append("scenes.json: 'scenes' 列表为空")

        template_type = template_data.get("id", "system_evolution")

        # 3. Node / Recipe reference checks
        all_valid_nodes = self.known_nodes | set(self.aliases.keys())
        for idx, scene in enumerate(scenes, 1):
            sid = scene.get("scene") or f"{idx:02d}"
            stype = scene.get("scene_type", "")

            # System Evolution checks
            if template_type == "system_evolution" or scene.get("graph"):
                g_nodes = scene.get("graph", {}).get("nodes", [])
                for n in g_nodes:
                    if n not in all_valid_nodes:
                        errors.append(f"Scene {sid}: 引用了未在 arch-graph.js 定义的节点 '{n}'")

                for a_idx, act in enumerate(scene.get("actions", []), 1):
                    atype = act.get("type")
                    if atype in ("node", "add_node", "highlight", "focus"):
                        target = act.get("target") or act.get("id")
                        if target and target not in all_valid_nodes:
                            errors.append(f"Scene {sid} action #{a_idx} ({atype}): 未知节点 '{target}'")
                    elif atype in ("connect", "packet"):
                        n_from = act.get("from")
                        n_to = act.get("to")
                        if n_from and n_from not in all_valid_nodes:
                            errors.append(f"Scene {sid} action #{a_idx} ({atype}): 未知起点节点 '{n_from}'")
                        if n_to and n_to not in all_valid_nodes:
                            errors.append(f"Scene {sid} action #{a_idx} ({atype}): 未知终点节点 '{n_to}'")

            # Estimation Template checks
            elif template_type == "estimation":
                if stype == "calc_step" and not scene.get("calc_board"):
                    errors.append(f"Scene {sid}: calc_step 分镜缺少 'calc_board' 结构定义")

            # Algorithm Template checks
            elif template_type == "algorithm":
                if stype == "hash_ring" and not scene.get("ring") and not scene.get("actions"):
                    errors.append(f"Scene {sid}: hash_ring 分镜缺少 'ring' 或 'actions' 定义")
                elif stype == "token_bucket" and not scene.get("bucket") and not scene.get("actions"):
                    errors.append(f"Scene {sid}: token_bucket 分镜缺少 'bucket' 或 'actions' 定义")
                elif stype in ("algo_viz", "edge_case") and not any(
                    scene.get(k)
                    for k in (
                        "array",
                        "linked_list",
                        "hash_map",
                        "tree",
                        "stack",
                        "dp_table",
                        "ring",
                        "bucket",
                        "sliding_window",
                        "steps",
                        "actions",
                    )
                ):
                    errors.append(f"Scene {sid}: algorithm 分镜缺少可视化结构或 actions")

            # Required narration
            if not scene.get("narration") and not scene.get("beats"):
                errors.append(f"Scene {sid}: 缺少 'narration' 口播文案")

        # 4. Template recipe checks
        recipe_types = [step.get("scene_type") for step in template_data.get("scene_recipe", [])]
        actual_types = [s.get("scene_type") for s in scenes]
        if "hook" in recipe_types and "hook" not in actual_types:
            errors.append("缺少必选镜头: 'hook'")
        if "summary" in recipe_types and "summary" not in actual_types:
            errors.append("缺少必选镜头: 'summary'")

        return errors

    def compile(
        self,
        entry: dict,
        chapter_data: dict,
        scenes_data: dict,
        template_data: dict,
    ) -> dict:
        """Compile and resolve semantic tiers, summary cards, and defaults."""
        errors = self.validate(entry, chapter_data, scenes_data, template_data)
        if errors:
            err_msg = f"[COMPILE ERROR] Validation failed for {entry.get('id', 'item')}:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(err_msg)

        compiled = copy.deepcopy(scenes_data)
        compiled["id"] = entry.get("id") or chapter_data.get("id")
        compiled["title"] = chapter_data.get("title") or entry.get("title_zh") or compiled.get("title")
        compiled["template"] = template_data.get("id", "system_evolution")
        compiled["course_id"] = self.course_info.get("id", self.course_id)
        compiled["course_name"] = self.course_info.get("name", self.course_id)
        compiled["theme"] = self.course_info.get("theme", {})
        compiled["target_duration_sec"] = float(
            chapter_data.get("target_duration_sec")
            or entry.get("target_duration_sec")
            or compiled.get("target_duration_sec", 57.0)
        )
        compiled["attribution"] = chapter_data.get("attribution") or self.course_info.get("attribution", "")
        compiled["memory_sentence"] = chapter_data.get("memory_sentence", "")

        avatar_tiers = self.avatar_config.get("tiers", {})
        default_tier_name = self.avatar_config.get("default_tier", "support")

        # Map template recipes for defaults
        recipe_map = {step["scene_type"]: step for step in template_data.get("scene_recipe", [])}

        concepts = chapter_data.get("concepts", [])

        for idx, scene in enumerate(compiled.get("scenes", []), 1):
            stype = scene.get("scene_type", "evolve")
            recipe = recipe_map.get(stype, {})

            # 1. Resolve avatar
            if "avatar" not in scene:
                tier_name = scene.get("avatar_tier") or recipe.get("default_avatar_tier") or default_tier_name
                tier_cfg = avatar_tiers.get(tier_name, avatar_tiers.get(default_tier_name, {}))
                scene["avatar"] = {
                    "state": tier_name,
                    "size": tier_cfg.get("size", 180),
                    "position": tier_cfg.get("position", "bottom_right"),
                }
            elif "size" not in scene["avatar"] or "position" not in scene["avatar"]:
                state = scene["avatar"].get("state", default_tier_name)
                tier_cfg = avatar_tiers.get(state, avatar_tiers.get(default_tier_name, {}))
                scene["avatar"].setdefault("size", tier_cfg.get("size", 180))
                scene["avatar"].setdefault("position", tier_cfg.get("position", "bottom_right"))

            # 2. Auto-fill summary concept cards if omitted
            if stype == "summary":
                if "cards" not in scene and concepts:
                    classes = ["active", "success", "warning"]
                    scene["cards"] = [
                        {
                            "title": f"{c_idx + 1}. {c.get('name', '')}",
                            "desc": c.get("l1_one_liner", ""),
                            "cls": classes[c_idx % len(classes)],
                        }
                        for c_idx, c in enumerate(concepts[:3])
                    ]
                if not scene.get("actions"):
                    cards_actions = []
                    for c_idx, c in enumerate(concepts[:3]):
                        c_title = f"{c_idx + 1}. {c.get('name')}: {c.get('l1_one_liner', '')}"
                        cards_actions.append({
                            "type": "card",
                            "index": c_idx + 1,
                            "title": c_title,
                            "at": round(0.6 + c_idx * 1.2, 2),
                        })
                    scene["actions"] = cards_actions

        # 3. Auto-append 'preview' (下集预告) scene for chapters if omitted
        has_preview = any(s.get("scene_type") == "preview" for s in compiled.get("scenes", []))
        if not has_preview and "chapters" in str(entry.get("dir", "")):
            current_cid = str(entry.get("id", "")).strip()
            chapters_list = self.catalog.get("chapters", [])
            next_chapter = None
            for c_i, ch in enumerate(chapters_list):
                if str(ch.get("id")) == current_cid or ch.get("slug") == current_cid:
                    if c_i + 1 < len(chapters_list):
                        next_chapter = chapters_list[c_i + 1]
                    break
            if next_chapter:
                next_num = str(next_chapter.get("id", "01"))
                next_t = next_chapter.get("title_zh") or next_chapter.get("title", "精彩进阶专题")
                preview_idx = len(compiled.get("scenes", []))
                course_title = self.course_info.get("name", "系统设计面试通关课")
                badge_prefix = self.course_info.get("theme", {}).get("badge_prefix", "下集预告")
                compiled["scenes"].append({
                    "scene": f"{preview_idx:02d}",
                    "id": f"{preview_idx:02d}_preview",
                    "scene_type": "preview",
                    "title": f"下集预告：{next_t}",
                    "badge": f"{badge_prefix} · NEXT EPISODE",
                    "next_title": f"第 {int(next_num) if next_num.isdigit() else next_num} 讲 · {next_t}",
                    "narration": f"下集预告：掌握了本节核心逻辑，下一集我们带来第 {int(next_num) if next_num.isdigit() else next_num} 讲：{next_t}。记得点赞关注不迷路！",
                    "keywords": [next_t, "下集预告", "关注追更"],
                    "mood": "conclusion",
                    "avatar_tier": "host",
                    "avatar": {
                        "state": "host",
                        "size": avatar_tiers.get("host", {}).get("size", 280),
                        "position": avatar_tiers.get("host", {}).get("position", "center_bottom"),
                    },
                    "teasers": [
                        f"深入拆解 {next_t} 核心机制与考点",
                        "算法与高并发架构经典设计模式",
                        "大厂高频面试关键解题逻辑",
                    ],
                    "cta": f"🔔 关注主播 · 追更《{course_title}》",
                    "actions": []
                })

        return compiled

    def compile_target(
        self,
        chapter_id: str | None = None,
        short_id: str | None = None,
        dir_path: str | Path | None = None,
        out_file: Path | None = None,
    ) -> Path:
        """Full flow: Resolve -> Load -> Sniff Template -> Compile -> Save -> Return Path."""
        entry, target_dir = self.resolve_entry(chapter_id, short_id, dir_path)
        chapter_file = target_dir / "chapter.json"
        scenes_file = target_dir / "scenes.json"

        chapter_data = load_json(chapter_file)
        scenes_data = load_json(scenes_file)

        template_name = chapter_data.get("template") or entry.get("template") or sniff_template_type(chapter_data, scenes_data)
        template_file = self.root / "templates" / f"{template_name}.json"
        if not template_file.exists():
            template_file = self.root / "templates" / "system_evolution.json"
        template_data = load_json(template_file)

        compiled = self.compile(entry, chapter_data, scenes_data, template_data)

        if out_file is None:
            out_file = target_dir / "compiled_spec.json"

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(json.dumps(compiled, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[*] Compiled {entry.get('id', 'spec')} (course: {self.course_id}, template: {template_name}) -> {out_file}")
        return out_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Universal Multi-Course Video Chapter Compiler")
    parser.add_argument("--course", default="demo", help="Course ID under content/courses/")
    parser.add_argument("--chapter", help="Chapter ID/slug (e.g. 01 or 02 or estimation)")
    parser.add_argument("--short", help="Short ID/slug (e.g. 01-redis-read)")
    parser.add_argument("--dir", help="Direct directory containing chapter.json & scenes.json")
    parser.add_argument("--out", help="Output path for compiled JSON")
    parser.add_argument("--validate-all", action="store_true", help="Validate all ready entries in catalog")
    args = parser.parse_args()

    compiler = ChapterCompiler(course_id=args.course)

    if args.validate_all:
        ready_count = 0
        courses_to_check = [args.course] if args.course != "all" else []
        if not courses_to_check:
            courses_dir = ROOT / "content" / "courses"
            if courses_dir.exists():
                courses_to_check = [d.name for d in courses_dir.iterdir() if d.is_dir()]
            else:
                courses_to_check = ["demo"]

        for cid in courses_to_check:
            comp = ChapterCompiler(course_id=cid)
            for ch in comp.catalog.get("chapters", []):
                if ch.get("status") == "ready":
                    out = comp.compile_target(chapter_id=ch["id"])
                    ready_count += 1
            for sh in comp.catalog.get("shorts", []):
                if sh.get("status") == "ready":
                    out = comp.compile_target(short_id=sh["id"])
                    ready_count += 1
        print(f"\n[SUCCESS] Validated and compiled {ready_count} ready entries successfully across {len(courses_to_check)} course(s)!")
        return

    if not (args.chapter or args.short or args.dir):
        parser.print_help()
        sys.exit(1)

    out_p = Path(args.out) if args.out else None
    compiler.compile_target(
        chapter_id=args.chapter,
        short_id=args.short,
        dir_path=args.dir,
        out_file=out_p,
    )


if __name__ == "__main__":
    main()
