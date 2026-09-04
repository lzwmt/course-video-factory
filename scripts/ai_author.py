#!/usr/bin/env python3
"""Universal AI authoring agent: Markdown lecture → chapter.json + scenes.json."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


SYSTEM_PROMPT = """你是系统设计架构师、课程编剧和 JSON 数据工程师。根据完整 Markdown 教材与 knowledge.json，生成可编译的 chapter.json 和 scenes.json。只使用教材明确出现的技术事实、数字、公式、组件、故障和权衡；不得编造。每个概念和场景都应尽量用 source_refs 指向 knowledge.json 的项目。

输出对象必须是 {\"chapter\": {...}, \"scenes\": {\"scenes\": [...]}}。chapter 必填 id, slug, title, title_zh, source, attribution, template, learning_goal, memory_sentence, core_problem, target_duration_sec (45-75), concepts (3-5 个且含 id/name/l1_one_liner/l2_principle/l3_engineering/visual), mainline, extension。template 只能是 system_evolution、estimation、algorithm。

scenes 必须有 6-8 个镜头，包含 hook 与 summary；system_evolution 应包含 problem、至少一个 evolve、flow；algorithm 应包含 naive、至少一个 algo_viz/hash_ring/token_bucket/sliding_window/code；estimation 应包含 assumptions、至少一个 calc_step（含 calc_board）、units_ladder。每镜含 scene、id、scene_type、title、badge、keywords、mood、narration、actions。旁白口语化、适合 TTS，数字和公式与教材一致。

"""


def _llm_chat(messages: list[dict], model: str = "gemini-3.7-flash-tiered") -> str:
    base = (
        os.environ.get("ANTIGRAVITY_BASE_URL")
        or os.environ.get("NOAGY_BASE_URL")
        or os.environ.get("OPENAI_API_BASE")
        or "http://127.0.0.1:51200"
    ).rstrip("/")
    key = os.environ.get("ROTATOR_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
    url = f"{base}/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def fallback_lru(course_info: dict, chapter_id: str) -> dict:
    prefix = course_info.get("theme", {}).get("badge_prefix", "算法精讲")
    return {
        "chapter": {
            "id": chapter_id,
            "title": "LRU Cache",
            "title_zh": "LRU 缓存（哈希 + 双向链表）",
            "template": "algorithm",
            "attribution": "LeetCode 146 · 经典高频设计题",
            "memory_sentence": "哈希定位，链表记账；头新尾旧，满了踢尾。",
            "target_duration_sec": 55,
            "concepts": [
                {"name": "O(1) 定位", "l1_one_liner": "HashMap 把 key 直接映射到链表节点"},
                {"name": "访问顺序", "l1_one_liner": "双向链表头部最新、尾部最久未用"},
                {"name": "满容淘汰", "l1_one_liner": "put 时容量满则删除链表尾节点"},
            ],
        },
        "scenes": {
            "scenes": [
                {
                    "scene": "00",
                    "scene_type": "hook",
                    "title": "LRU：面试官最爱的缓存题",
                    "badge": f"{prefix} · LRU Cache",
                    "keywords": ["O(1)", "淘汰", "热度"],
                    "mood": "warning",
                    "narration": "LeetCode 一百四十六，LRU 缓存。面试官要的不是会用 LinkedHashMap，而是你亲手把哈希和链表焊在一起。",
                    "actions": [{"type": "counter", "from": 1, "to": 146, "at": 0.6}],
                },
                {
                    "scene": "01",
                    "scene_type": "naive",
                    "title": "数组扫一遍？超时警告",
                    "badge": f"{prefix} · Naive",
                    "keywords": ["O(n)", "扫描", "超时"],
                    "mood": "warning",
                    "problem_text": "用数组维护访问顺序，每次 get/put 都线性扫描，复杂度 O(n)，大数据必超时。",
                    "narration": "朴素做法拿数组记账，每次访问都从头扫到尾。数据一大，时间复杂度直接爆炸。",
                    "actions": [],
                },
                {
                    "scene": "02",
                    "scene_type": "code",
                    "title": "哈希定位 + 链表记账",
                    "badge": f"{prefix} · 核心结构",
                    "keywords": ["HashMap", "链表", "O(1)"],
                    "mood": "normal",
                    "code": True,
                    "code_lines": [
                        "map: key -> node",
                        "list: head=newest, tail=oldest",
                        "get: move node to head",
                        "put: insert head; evict tail if full",
                    ],
                    "narration": "正确解法是哈希表加双向链表。哈希负责 O(1) 找到节点，链表负责记住谁最新、谁该被踢。",
                    "actions": [],
                },
                {
                    "scene": "03",
                    "scene_type": "algo_viz",
                    "title": "get 命中：节点挪到头部",
                    "badge": f"{prefix} · get",
                    "keywords": ["命中", "刷新", "头部"],
                    "mood": "normal",
                    "steps": [
                        {"label": "定位", "text": "HashMap 用 key 直接找到链表节点，O(1)"},
                        {"label": "摘下", "text": "断开该节点的 prev / next，从原位置移出"},
                        {"label": "插头", "text": "接到 head 后面，标记为刚刚用过"},
                    ],
                    "narration": "get 命中后，不能只返回值，必须把该节点从原位置摘下，再插到链表头，表示刚刚用过。",
                    "actions": [],
                },
                {
                    "scene": "04",
                    "scene_type": "edge_case",
                    "title": "put 满了：踢掉链表尾",
                    "badge": f"{prefix} · evict",
                    "keywords": ["容量", "淘汰", "尾部"],
                    "mood": "warning",
                    "steps": [
                        {"label": "满容", "text": "size == capacity 时先淘汰，再插入"},
                        {"label": "踢尾", "text": "删除链表尾节点，并从 HashMap 去掉该 key"},
                        {"label": "插头", "text": "新节点放头部；重复 put 同一 key 则更新值并刷新热度"},
                    ],
                    "narration": "put 新键时若容量已满，先删链表尾和对应哈希项，再把新节点插到头部。重复 put 同一 key 要更新并刷新热度。",
                    "actions": [],
                },
                {
                    "scene": "05",
                    "scene_type": "summary",
                    "title": "三句话带走 LRU",
                    "badge": f"{prefix} · 总结",
                    "keywords": ["哈希", "链表", "踢尾"],
                    "mood": "conclusion",
                    "narration": "记住口诀：哈希定位，链表记账；头新尾旧，满了踢尾。这就是 LRU 的工业级写法。",
                    "cta": "👉 下一题：Two Sum 哈希一遍过",
                    "actions": [],
                },
            ]
        },
    }


def author(
    course_id: str,
    chapter: str,
    input_md: Path,
    produce: bool = False,
    send_mac: bool = False,
    max_retries: int = 3,
) -> Path:
    from scripts.compile_chapter import ChapterCompiler

    compiler = ChapterCompiler(course_id=course_id)
    course_info = compiler.course_info
    md_text = input_md.read_text(encoding="utf-8") if input_md.exists() else ""

    payload = None
    last_err = ""
    for attempt in range(1, max_retries + 1):
        try:
            user = (
                f"课程: {course_info.get('name')} ({course_id})\n"
                f"badge_prefix: {course_info.get('theme', {}).get('badge_prefix')}\n"
                f"chapter_id: {chapter}\n"
                f"requested_template: {next((x.get('template') for x in compiler.catalog.get('chapters', []) if str(x.get('id')) == str(chapter)), 'system_evolution')}\n"
            )
            if last_err:
                user += f"\n上次编译失败，请修复：\n{last_err}\n"
            knowledge_path = next(iter((ROOT / "content" / "chapters").glob(f"{chapter[:2]}-*/knowledge.json")), None)
            if knowledge_path and knowledge_path.exists():
                user += f"\n技术事实索引 knowledge.json（只能依据其中的 source_excerpt，不得编造）：\n{knowledge_path.read_text(encoding="utf-8")}\n"
            user += f"\n讲义 Markdown:\n{md_text}\n"
            raw = _llm_chat([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ])
            payload = _extract_json(raw)
            if "chapter" not in payload or "scenes" not in payload:
                raise ValueError("LLM JSON missing chapter/scenes")
        except Exception as e:
            print(f"[ai_author] LLM attempt {attempt} failed: {e}")
            payload = None
            last_err = str(e)

        if payload is None:
            if attempt == max_retries:
                raise RuntimeError(f"AI generation failed for {chapter}: {last_err}")
            continue
        # Keep catalog paths under content/chapters unless a course-specific path is configured.
        entry = next((x for x in compiler.catalog.get("chapters", []) if str(x.get("id")) == str(chapter) or x.get("slug") == chapter), None)
        ch_dir = ROOT / str(entry.get("dir")) if entry and entry.get("dir") else compiler.course_dir / "chapters" / chapter
        ch_dir.mkdir(parents=True, exist_ok=True)
        chapter_data = payload["chapter"]
        chapter_data.setdefault("id", chapter)
        chapter_data.setdefault("template", course_info.get("default_template", "algorithm"))
        scenes_data = payload["scenes"]
        if isinstance(scenes_data, list):
            scenes_data = {"scenes": scenes_data}
        (ch_dir / "chapter.json").write_text(
            json.dumps(chapter_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (ch_dir / "scenes.json").write_text(
            json.dumps(scenes_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        catalog = compiler.catalog
        chapters = catalog.setdefault("chapters", [])
        if not any(c.get("id") == chapter or c.get("slug") == chapter for c in chapters):
            chapters.append({
                "id": chapter.split("-")[0] if chapter[:2].isdigit() else chapter,
                "slug": chapter,
                "title": chapter_data.get("title", chapter),
                "title_zh": chapter_data.get("title_zh", chapter_data.get("title", chapter)),
                "template": chapter_data.get("template"),
                "status": "ready",
                "dir": str(ch_dir.relative_to(ROOT)),
                "target_duration_sec": chapter_data.get("target_duration_sec", 55),
            })
            catalog["total_chapters"] = len(chapters)
            catalog["course_id"] = course_id
            catalog["course_name"] = course_info.get("name", course_id)
            compiler.catalog_file.parent.mkdir(parents=True, exist_ok=True)
            compiler.catalog_file.write_text(
                json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

        try:
            out = compiler.compile_target(dir_path=ch_dir)
            print(f"[ai_author] compile ok: {out}")
            break
        except Exception as e:
            last_err = str(e)
            print(f"[ai_author] compile failed attempt {attempt}: {e}")
            if attempt == max_retries:
                raise RuntimeError(f"AI output for {chapter} did not compile after {max_retries} attempts: {last_err}")

    if produce:
        cmd = [
            sys.executable, str(ROOT / "scripts" / "produce_pipeline.py"),
            "--course", course_id,
            "--dir" if False else "--chapter", chapter,
            "--out", str(ROOT / "outputs" / f"pipeline_{course_id}_{chapter.replace('-', '_')}"),
        ]
        # produce uses --chapter; resolve by dir if slug
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "produce_pipeline.py"),
                "--course", course_id,
                "--chapter", chapter,
                "--out", str(ROOT / "outputs" / f"pipeline_{course_id}_{chapter.replace('-', '_')}"),
            ],
            cwd=str(ROOT),
            check=True,
        )
        final_mp4 = ROOT / "outputs" / f"pipeline_{course_id}_{chapter.replace('-', '_')}" / "final.mp4"
        if send_mac and final_mp4.exists():
            dest = f"mac:~/Downloads/{course_id}-{chapter}.mp4"
            subprocess.run(["scp", str(final_mp4), dest], check=True)
            print(f"[ai_author] sent {final_mp4} -> {dest}")
        return final_mp4 if final_mp4.exists() else ch_dir

    return ch_dir


def main() -> None:
    p = argparse.ArgumentParser(description="AI Author: Markdown → course chapter pack")
    p.add_argument("--course", required=True)
    p.add_argument("--chapter", required=True)
    p.add_argument("--input", help="Markdown lecture path; defaults to content/source/<chapter>.md")
    p.add_argument("--produce", action="store_true")
    p.add_argument("--send-mac", action="store_true")
    p.add_argument("--max-retries", type=int, default=3)
    args = p.parse_args()
    input_path = Path(args.input) if args.input else (next(iter((ROOT / "content" / "source").glob(f"{args.chapter[:2]}-*.md")), ROOT / "content" / "source" / f"{args.chapter[:2]}.md"))
    author(
        course_id=args.course,
        chapter=args.chapter,
        input_md=input_path,
        produce=args.produce,
        max_retries=args.max_retries,
    )


if __name__ == "__main__":
    main()
