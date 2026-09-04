#!/usr/bin/env python3
"""Publish-pack factory: cover.png, cover_bilibili.png, publish_meta.json."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FONT_REGULAR = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT_BLACK = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc")
FALLBACK_FONT = Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
COVER_TIME_SEC = 1.5


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def format_ts(seconds: float) -> str:
    total = max(0, int(round(float(seconds))))
    minutes, secs = divmod(total, 60)
    return f"{minutes:02d}:{secs:02d}"


def wrap_title(title: str, width: int = 14) -> list[str]:
    title = (title or "").strip()
    if not title:
        return [""]
    if len(title) <= width:
        return [title]
    lines: list[str] = []
    buf = title
    while buf and len(lines) < 3:
        lines.append(buf[:width])
        buf = buf[width:]
    return lines


def _scenes(spec: dict) -> list[dict]:
    items = spec.get("scenes") or spec.get("shots") or []
    return [s for s in items if isinstance(s, dict)]


def collect_keywords(spec: dict, limit: int = 6) -> list[str]:
    seen: list[str] = []
    for scene in _scenes(spec):
        for kw in scene.get("keywords") or []:
            text = str(kw).strip()
            if text and text not in seen:
                seen.append(text)
            if len(seen) >= limit:
                return seen
    return seen


def build_chapter_markers(spec: dict) -> list[dict]:
    markers: list[dict] = []
    t = 0.0
    for scene in _scenes(spec):
        title = str(scene.get("title") or scene.get("id") or scene.get("scene") or "镜头")
        markers.append({"time": format_ts(t), "title": title})
        t += float(scene.get("total_duration_sec") or scene.get("duration_sec") or 0.0)
    return markers


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def _fontfile() -> str:
    font = FONT_BLACK if FONT_BLACK.exists() else (FONT_REGULAR if FONT_REGULAR.exists() else FALLBACK_FONT)
    return str(font).replace("\\", "/").replace(":", "\\:")


def _run(cmd: list[str]) -> None:
    print(f"\n[RUN] {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _pick_cover_source(out_dir: Path, final_mp4: Path | None = None) -> Path | None:
    candidates = [
        out_dir / "shots" / "shot_00.mp4",
        out_dir / "shots" / "00.mp4",
        out_dir / "lecture_courseware.mp4",
        final_mp4,
        out_dir / "final.mp4",
    ]
    shots_dir = out_dir / "shots"
    if shots_dir.exists():
        numbered = sorted(shots_dir.glob("*.mp4"))
        candidates.extend(numbered[:1])
    for path in candidates:
        if path and Path(path).exists():
            return Path(path)
    return None


def extract_cover_frame(source: Path, dest: Path, t: float = COVER_TIME_SEC) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(source),
        "-frames:v", "1",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b0f19",
        str(dest),
    ])
    return dest


def enhance_cover(
    raw_png: Path,
    cover_png: Path,
    badge: str,
    title: str,
    keywords: list[str],
    primary: str = "#3B82F6",
) -> Path:
    font = _fontfile()
    title_lines = wrap_title(title, 12)
    kw = "  ·  ".join(keywords[:4])
    filters = [
        "format=rgba",
        "drawbox=x=0:y=0:w=1080:h=220:color=0x0b0f19@0.55:t=fill",
        "drawbox=x=0:y=1480:w=1080:h=440:color=0x0b0f19@0.72:t=fill",
        f"drawbox=x=56:y=96:w=520:h=64:color={primary.replace('#', '0x')}@0.92:t=fill",
        (
            f"drawtext=fontfile='{font}':text='{_escape_drawtext(badge[:18])}'"
            ":fontsize=28:fontcolor=white:x=76:y=110"
        ),
    ]
    y = 1560
    for i, line in enumerate(title_lines):
        filters.append(
            f"drawtext=fontfile='{font}':text='{_escape_drawtext(line)}'"
            f":fontsize=52:fontcolor=white:x=64:y={y + i * 64}"
        )
    if kw:
        filters.append(
            f"drawtext=fontfile='{font}':text='{_escape_drawtext(kw)}'"
            ":fontsize=28:fontcolor=0xFDE68A:x=64:y=1820"
        )
    _run([
        "ffmpeg", "-y", "-i", str(raw_png),
        "-vf", ",".join(filters),
        str(cover_png),
    ])
    return cover_png


def make_bilibili_cover(cover_png: Path, dest: Path) -> Path:
    """16:9 landscape companion cover for Bilibili."""
    _run([
        "ffmpeg", "-y", "-i", str(cover_png),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
        str(dest),
    ])
    return dest


def make_solid_cover(dest: Path, badge: str, title: str, keywords: list[str], bg: str = "0x0b0f19") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    font = _fontfile()
    title_lines = wrap_title(title, 12)
    kw = "  ·  ".join(keywords[:4])
    draws = [
        f"drawtext=fontfile='{font}':text='{_escape_drawtext(badge[:18])}'"
        ":fontsize=36:fontcolor=white:x=80:y=240",
    ]
    for i, line in enumerate(title_lines):
        draws.append(
            f"drawtext=fontfile='{font}':text='{_escape_drawtext(line)}'"
            f":fontsize=64:fontcolor=white:x=80:y={480 + i * 80}"
        )
    if kw:
        draws.append(
            f"drawtext=fontfile='{font}':text='{_escape_drawtext(kw)}'"
            ":fontsize=32:fontcolor=0xFDE68A:x=80:y=1600"
        )
    _run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={bg}:s=1080x1920:d=1",
        "-frames:v", "1",
        "-vf", ",".join(draws),
        str(dest),
    ])
    return dest


def build_platform_copy(
    course_id: str,
    chapter_id: str,
    title: str,
    badge_prefix: str,
    keywords: list[str],
    markers: list[dict],
    summary: str = "",
) -> dict:
    tags_plain = keywords[:5] or [badge_prefix, "系统设计", "面试"]
    hash_tags = [f"#{t.lstrip('#')}" for t in (["程序员", badge_prefix, "系统设计", "后端面试", "技术分享"])]
    timeline = "\n".join(f"{m['time']} {m['title']}" for m in markers)
    desc_body = summary or f"本期讲解{title}。"
    return {
        "bilibili": {
            "title": f"【{badge_prefix}】{title}",
            "tags": tags_plain,
            "desc": f"{desc_body}\n\n时间轴：\n{timeline}",
            "cover": "cover_bilibili.png",
        },
        "xiaohongshu": {
            "title": f"大厂架构面试必考！{title} 🔥",
            "tags": hash_tags,
            "desc": f"面试官问到相关系统设计题，先记住这条主线：{title}。跟着图解走一遍比死记组件名有用。",
        },
        "douyin": {
            "title": f"{badge_prefix} {chapter_id}：{title} #程序员 #系统设计 #计算机",
            "tags": tags_plain[:3],
        },
    }


def build_publish_meta(
    course_id: str,
    chapter_id: str,
    spec: dict,
    duration: float | None = None,
    course_info: dict | None = None,
) -> dict:
    course = course_info or {}
    theme = course.get("theme") or {}
    title = str(spec.get("title") or spec.get("title_zh") or f"第 {chapter_id} 章")
    scenes = _scenes(spec)
    if duration is None:
        duration = float(spec.get("total_duration_sec") or spec.get("target_duration_sec") or 0.0)
        if not duration:
            duration = sum(float(s.get("total_duration_sec") or s.get("duration_sec") or 0.0) for s in scenes)
    markers = build_chapter_markers(spec)
    keywords = collect_keywords(spec)
    badge = theme.get("badge_prefix") or course.get("name") or course_id
    summary = str(spec.get("learning_goal") or spec.get("memory_sentence") or "")
    return {
        "course_id": course_id,
        "chapter_id": str(chapter_id),
        "title": title,
        "durations": round(float(duration), 1),
        "platforms": build_platform_copy(
            course_id, str(chapter_id), title, str(badge), keywords, markers, summary
        ),
        "chapter_markers": markers,
    }


def package_output(
    out_dir: Path,
    spec_path: Path | None = None,
    course_id: str = "system-design",
    chapter_id: str = "01",
    course_info: dict | None = None,
    final_mp4: Path | None = None,
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timed = out_dir / "shots_timed.json"
    spec: dict = {}
    if spec_path and Path(spec_path).exists():
        spec = load_json(Path(spec_path))
    if timed.exists():
        timed_spec = load_json(timed)
        if timed_spec:
            spec = timed_spec
    final_mp4 = Path(final_mp4) if final_mp4 else out_dir / "final.mp4"
    duration = None
    if final_mp4.exists():
        try:
            from scripts.qa_render import probe_media
            meta = probe_media(final_mp4)
            duration = float((meta.get("format") or {}).get("duration") or 0.0) or None
        except Exception:
            duration = None

    cover = out_dir / "cover.png"
    raw = out_dir / "cover_raw.png"
    bili = out_dir / "cover_bilibili.png"
    title = str(spec.get("title") or f"第 {chapter_id} 章")
    keywords = collect_keywords(spec)
    theme = (course_info or {}).get("theme") or {}
    badge = str(theme.get("badge_prefix") or "系统设计全书")
    source = _pick_cover_source(out_dir, final_mp4)
    try:
        if source:
            extract_cover_frame(source, raw)
            enhance_cover(raw, cover, badge=f"{badge} · {chapter_id}", title=title, keywords=keywords,
                          primary=str(theme.get("primary_color") or "#3B82F6"))
        else:
            make_solid_cover(cover, badge=f"{badge} · {chapter_id}", title=title, keywords=keywords)
        if cover.exists():
            make_bilibili_cover(cover, bili)
    except subprocess.CalledProcessError as exc:
        print(f"[publisher] cover ffmpeg failed: {exc}")
        if not cover.exists():
            make_solid_cover(cover, badge=f"{badge} · {chapter_id}", title=title, keywords=keywords)

    meta = build_publish_meta(course_id, chapter_id, spec, duration=duration, course_info=course_info)
    meta_path = out_dir / "publish_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[publisher] wrote {cover} and {meta_path}")
    return meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Package cover.png + publish_meta.json")
    parser.add_argument("--course", default="demo")
    parser.add_argument("--chapter")
    parser.add_argument("--short")
    parser.add_argument("--dir", required=True, help="Pipeline output directory")
    parser.add_argument("--spec", help="compiled_spec.json or shots_timed.json")
    args = parser.parse_args()

    from scripts.compile_chapter import ChapterCompiler
    compiler = ChapterCompiler(course_id=args.course)
    chapter_id = args.chapter or args.short or "01"
    spec = Path(args.spec) if args.spec else None
    if not spec and (args.chapter or args.short):
        try:
            _entry, target = compiler.resolve_entry(args.chapter, args.short)
            compiled = target / "compiled_spec.json"
            if compiled.exists():
                spec = compiled
            chapter_id = str(_entry.get("id") or chapter_id)
        except Exception:
            pass
    package_output(
        Path(args.dir),
        spec_path=spec,
        course_id=args.course,
        chapter_id=str(chapter_id),
        course_info=compiler.course_info,
    )


if __name__ == "__main__":
    main()
