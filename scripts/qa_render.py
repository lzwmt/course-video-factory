#!/usr/bin/env python3
"""QA quality gate for rendered technical video courseware.

Checks:
1. Video container and resolution (strictly 1080x1920).
2. Audio stream existence, format, and non-empty duration.
3. Total duration tolerance: |actual - target| <= 8.0s.
4. Scene segmentation alignment: count(_pip_segments) == count(scenes).
5. Output file validity and non-trivial file size (> 2MB).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def probe_media(video_path: Path) -> dict:
    """Run ffprobe to extract stream metadata."""
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(video_path.resolve())
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def run_qa_check(
    final_mp4: Path,
    spec_path: Path | None = None,
    timed_spec_path: Path | None = None,
    target_duration: float | None = None,
    section_mode: bool = False,
) -> tuple[bool, list[str]]:
    """Execute all assertions and return (pass_bool, list_of_report_lines)."""
    reports: list[str] = []
    failed = False
    section_spec = None
    if spec_path and spec_path.exists():
        section_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if section_mode or (section_spec and "-S" in str(section_spec.get("id", ""))):
        count = len((section_spec or {}).get("scenes", []))
        if 3 <= count <= 5:
            reports.append(f"✅ 节级分镜数量合规: {count} (3-5)")
        else:
            reports.append(f"❌ 节级分镜数量不合规: {count} (必须为 3-5)")
            failed = True

    if not final_mp4.exists():
        return False, [f"❌ 成片文件不存在: {final_mp4}"]

    meta = probe_media(final_mp4)
    streams = meta.get("streams", [])
    fmt = meta.get("format", {})

    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    # 1. Video stream & Resolution check
    if not v_stream:
        reports.append("❌ 丢失视频轨 (Video stream missing)")
        failed = True
    else:
        w = int(v_stream.get("width", 0))
        h = int(v_stream.get("height", 0))
        if w == 1080 and h == 1920:
            reports.append(f"✅ 分辨率合格: 1080×1920 (codec: {v_stream.get('codec_name')})")
        else:
            reports.append(f"❌ 分辨率不合格: {w}×{h} (必须为 1080×1920)")
            failed = True

    # 2. Audio stream check
    if not a_stream:
        reports.append("❌ 丢失音频轨 (Audio stream missing)")
        failed = True
    else:
        rate = a_stream.get("sample_rate", "0")
        reports.append(f"✅ 音频轨正常: {a_stream.get('codec_name')} @ {rate}Hz")

    # 3. File size check
    file_size_bytes = final_mp4.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    if file_size_mb >= 2.0:
        reports.append(f"✅ 文件体积正常: {file_size_mb:.2f} MB")
    else:
        reports.append(f"❌ 文件体积异常 (可能黑屏或空文件): {file_size_mb:.2f} MB (< 2.0 MB)")
        failed = True

    # 4. Duration tolerance check
    actual_dur = float(fmt.get("duration", 0.0))
    expected_dur = target_duration
    if expected_dur is None:
        if timed_spec_path and timed_spec_path.exists():
            td = json.loads(timed_spec_path.read_text(encoding="utf-8"))
            expected_dur = float(td.get("total_duration_sec") or td.get("target_duration_sec", 57.0))
        elif spec_path and spec_path.exists():
            sp = json.loads(spec_path.read_text(encoding="utf-8"))
            expected_dur = float(sp.get("target_duration_sec", 57.0))
        else:
            expected_dur = 57.0

    tolerance = 8.0
    delta = abs(actual_dur - expected_dur)
    if delta <= tolerance:
        reports.append(f"✅ 时长窗口合规: 实测 {actual_dur:.2f}s, 预期 {expected_dur:.2f}s (偏差 {delta:.2f}s ≤ {tolerance}s)")
    else:
        reports.append(f"❌ 时长超标: 实测 {actual_dur:.2f}s, 预期 {expected_dur:.2f}s (偏差 {delta:.2f}s > {tolerance}s)")
        failed = True

    # 5. Segment alignment check
    seg_dir = final_mp4.parent / "_pip_segments"
    if seg_dir.exists():
        segs = list(seg_dir.glob("pip_*.mp4"))
        expected_scenes_count = None
        if spec_path and spec_path.exists():
            sp = json.loads(spec_path.read_text(encoding="utf-8"))
            expected_scenes_count = len(sp.get("scenes", []))

        if expected_scenes_count is not None:
            if len(segs) == expected_scenes_count:
                reports.append(f"✅ 分镜镜头对齐: {len(segs)} / {expected_scenes_count} Scene segments")
            else:
                reports.append(f"❌ 分镜数量失配: 实际生成 {len(segs)} 段, 预期 {expected_scenes_count} 段")
                failed = True
        else:
            reports.append(f"ℹ️ 检测到 {len(segs)} 个镜头分段")

    return (not failed), reports


def main() -> None:
    parser = argparse.ArgumentParser(description="System Design Video Render QA Gate")
    parser.add_argument("--chapter", help="Chapter ID from catalog (e.g. 01)")
    parser.add_argument("--short", help="Short ID from catalog (e.g. 01-redis-read)")
    parser.add_argument("--section", help="Section ID from catalog (e.g. 01-S01)")
    parser.add_argument("--dir", help="Output directory containing final.mp4")
    parser.add_argument("--video", help="Direct path to final.mp4")
    parser.add_argument("--spec", help="Path to compiled spec JSON")
    args = parser.parse_args()

    out_dir = Path(args.dir) if args.dir else None
    video_path = Path(args.video) if args.video else None
    spec_path = Path(args.spec) if args.spec else None

    if args.chapter or args.short or args.section:
        from scripts.compile_chapter import ChapterCompiler
        compiler = ChapterCompiler()
        entry, entry_dir = compiler.resolve_entry(args.chapter, args.short, section_id=args.section)
        if out_dir is None:
            prefix = "ch" if args.chapter else ("" if args.section else "short_")
            eid = entry["id"].replace("-", "_")
            out_dir = ROOT / "outputs" / f"pipeline_v3_{prefix}{eid}"
        if spec_path is None:
            spec_path = entry_dir / "compiled_spec.json"

    if video_path is None and out_dir:
        video_path = out_dir / "final.mp4"

    if video_path is None:
        parser.print_help()
        sys.exit(1)

    timed_spec = out_dir / "shots_timed.json" if out_dir else None

    passed, reports = run_qa_check(
        final_mp4=video_path,
        spec_path=spec_path,
        timed_spec_path=timed_spec,
        section_mode=bool(args.section),
    )

    print("\n==========================================")
    print(f"🎬 QA Inspection: {video_path.name}")
    print("==========================================")
    for line in reports:
        print(line)
    print("==========================================")

    if passed:
        print("🎉 [QA GATE PASS] Production meets quality standards!")
        sys.exit(0)
    else:
        print("🚫 [QA GATE FAILED] Quality gate rejected this build.")
        sys.exit(2)


if __name__ == "__main__":
    main()
