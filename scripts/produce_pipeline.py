#!/usr/bin/env python3
"""Unified end-to-end video production pipeline.

Flow:
1. Shots Spec JSON -> TTS (Edge-TTS / Qwen3-TTS) -> Timed JSON + voice.wav
2. Timed JSON -> HyperFrames HTML compositions -> Headless Lecture Courseware MP4
3. voice.wav + Ryan.png -> Presenter Studio (pipeline.py) -> Digital Human MP4
4. Digital Human MP4 + Headless Lecture MP4 -> Composer (composer.py) -> Final PiP MP4
"""
from __future__ import annotations

import argparse
import fcntl
import json
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.presenter_paths import default_avatar_image, studio_python, studio_root

STUDIO = studio_root()
STUDIO_PYTHON = studio_python(STUDIO)
GPU_LOCK_PATH = ROOT / "outputs" / ".presenter_gpu.lock"


@contextmanager
def presenter_gpu_lock():
    """Serialize digital-human inference to avoid GPU OOM."""
    GPU_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GPU_LOCK_PATH, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)

def run_cmd(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n[RUN] {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)

def _avatar_overlay_xy(position: str, size: int) -> tuple[str, str]:
    pos = (position or "bottom_right").lower()
    if pos in ("bottom_left", "left"):
        return "40", f"main_h-overlay_h-120"
    if pos in ("center_bottom", "center", "host"):
        return "(main_w-overlay_w)/2", f"main_h-overlay_h-80"
    return "main_w-overlay_w-40", "main_h-overlay_h-120"


def ensure_sfx_assets() -> dict[str, Path]:
    sfx_dir = ROOT / "assets" / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    specs = {
        "error": "sine=frequency=160:duration=0.28",
        "success": "sine=frequency=880:duration=0.12",
    }
    out: dict[str, Path] = {}
    for name, src in specs.items():
        p = sfx_dir / f"{name}.wav"
        if not p.exists():
            run_cmd([
                "ffmpeg", "-y", "-f", "lavfi", "-i", src,
                "-af", "volume=0.35", "-ar", "44100", "-ac", "1", str(p),
            ])
        out[name] = p
    return out


def mix_scene_sfx(timed_spec: Path, final_mp4: Path) -> None:
    spec = json.loads(timed_spec.read_text(encoding="utf-8"))
    sfx_files = ensure_sfx_assets()
    cues: list[tuple[float, str]] = []
    t = 0.0
    used = set()
    for item in spec.get("scenes") or spec.get("shots") or []:
        dur = float(item.get("total_duration_sec") or item.get("duration_sec") or 5.0)
        for act in item.get("actions") or []:
            kind = act.get("sfx")
            if kind in sfx_files and kind not in used:
                used.add(kind)
                cues.append((t + float(act.get("at") or 0.8), kind))
        t += dur
    if not cues:
        return
    tmp = final_mp4.with_name(final_mp4.stem + "_nosfx.mp4")
    final_mp4.replace(tmp)
    inputs = ["-i", str(tmp)]
    fc = ["[0:a]volume=1.0[voice]"]
    mix_ins = ["[voice]"]
    for i, (when, kind) in enumerate(cues, start=1):
        inputs += ["-i", str(sfx_files[kind])]
        delay = int(when * 1000)
        fc.append(f"[{i}:a]volume=0.18,adelay={delay}|{delay}[sfx{i}]")
        mix_ins.append(f"[sfx{i}]")
    n = 1 + len(cues)
    fc.append(f"{''.join(mix_ins)}amix=inputs={n}:duration=first:dropout_transition=0[aout]")
    run_cmd([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", ";".join(fc),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(final_mp4),
    ])


def compose_lecture_only(timed_spec: Path, lecture: Path, final_mp4: Path, voice: Path | None = None) -> None:
    """Captions + SFX on courseware when digital human is unavailable."""
    from scripts.build_captions import build_all_captions
    from concurrent.futures import ThreadPoolExecutor

    spec = json.loads(timed_spec.read_text(encoding="utf-8"))
    items = spec.get("scenes") or spec.get("shots") or []
    captions = build_all_captions(timed_spec, final_mp4.parent)
    segs_dir = final_mp4.parent / "_pip_segments"
    segs_dir.mkdir(parents=True, exist_ok=True)
    concat_list = segs_dir / "concat.txt"
    voice = voice if voice and voice.exists() else final_mp4.parent / "voice.wav"
    tasks = []
    t = 0.0
    for item in items:
        sid = str(item.get("scene") or item.get("shot", "01"))
        dur = float(item.get("total_duration_sec") or item.get("duration_sec") or 5.0)
        out_seg = segs_dir / f"pip_{sid}.mp4"
        ass = captions.get(sid)
        tasks.append((sid, t, dur, out_seg, ass))
        t += dur

    def _render_segment(task) -> Path:
        sid, start_t, dur, out_seg, ass = task
        filt = (
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b0f19,setsar=1"
        )
        if ass and ass.exists():
            escaped = str(ass.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", r"\'")
            filt = f"{filt},ass='{escaped}'"
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_t:.3f}", "-t", f"{dur:.3f}", "-i", str(lecture.resolve()),
        ]
        if voice.exists():
            cmd += ["-ss", f"{start_t:.3f}", "-t", f"{dur:.3f}", "-i", str(voice.resolve())]
        cmd += [
            "-vf", filt,
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-map", "0:v",
        ]
        if voice.exists():
            cmd += ["-map", "1:a", "-c:a", "aac", "-ar", "16000", "-ac", "1", "-b:a", "192k"]
        cmd.append(str(out_seg))
        run_cmd(cmd)
        return out_seg

    with ThreadPoolExecutor(max_workers=4) as executor:
        rendered_segs = list(executor.map(_render_segment, tasks))
    lines = [f"file '{s.resolve()}'" for s in rendered_segs]
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        str(final_mp4.resolve()),
    ])
    mix_scene_sfx(timed_spec, final_mp4)


def compose_scene_avatars(timed_spec: Path, lecture: Path, presenter: Path, final_mp4: Path) -> None:
    from scripts.build_captions import build_all_captions
    from concurrent.futures import ThreadPoolExecutor

    spec = json.loads(timed_spec.read_text(encoding="utf-8"))
    items = spec.get("scenes") or spec.get("shots") or []
    captions = build_all_captions(timed_spec, final_mp4.parent)
    segs_dir = final_mp4.parent / "_pip_segments"
    segs_dir.mkdir(parents=True, exist_ok=True)
    concat_list = segs_dir / "concat.txt"
    tasks = []
    t = 0.0
    for item in items:
        sid = str(item.get("scene") or item.get("shot", "01"))
        dur = float(item.get("total_duration_sec") or item.get("duration_sec") or 5.0)
        avatar = item.get("avatar") or {}
        size = int(avatar.get("size") or 180)
        pos_x, pos_y = _avatar_overlay_xy(str(avatar.get("position") or "bottom_right"), size)
        r = size // 2
        out_seg = segs_dir / f"pip_{sid}.mp4"
        ass = captions.get(sid)
        tasks.append((sid, t, dur, size, pos_x, pos_y, r, out_seg, ass))
        t += dur

    voice_wav = final_mp4.parent / "voice.wav"
    wav_dir = final_mp4.parent / "wav"

    def _render_pip_segment(task) -> Path:
        sid, start_t, dur, size, pos_x, pos_y, r, out_seg, ass = task
        ass_filter = ""
        if ass and ass.exists():
            escaped = str(ass.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", r"\'")
            ass_filter = f";[v_over]ass='{escaped}'[vout]"
            overlay_out = "[v_over]"
        else:
            overlay_out = "[vout]"
        filt = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0b0f19,setsar=1[bg];"
            f"[1:v]scale={size}:{size}:force_original_aspect_ratio=increase,"
            f"crop={size}:{size},format=yuva420p,"
            f"geq='p(X,Y)':a='if(lte(hypot(X-{r},Y-{r}),{r}),255,0)'[av];"
            f"[bg][av]overlay={pos_x}:{pos_y}{overlay_out}"
            f"{ass_filter}"
        )
        seg_wav = wav_dir / f"item{sid}_beat01.wav"
        if not seg_wav.exists() and sid.isdigit():
            p_id = f"{int(sid):02d}"
            cand = wav_dir / f"item{p_id}_beat01.wav"
            if cand.exists():
                seg_wav = cand

        audio_inputs = []
        audio_map = []
        if seg_wav.exists():
            audio_inputs = ["-i", str(seg_wav.resolve())]
            audio_map = ["-map", "2:a"]
        elif voice_wav.exists():
            audio_inputs = ["-ss", f"{start_t:.3f}", "-t", f"{dur:.3f}", "-i", str(voice_wav.resolve())]
            audio_map = ["-map", "2:a"]
        else:
            audio_map = ["-map", "1:a?"]

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_t:.3f}", "-t", f"{dur:.3f}", "-i", str(lecture.resolve()),
            "-stream_loop", "-1", "-ss", f"{start_t:.3f}", "-t", f"{dur:.3f}", "-i", str(presenter.resolve()),
        ] + audio_inputs + [
            "-filter_complex", filt,
            "-map", "[vout]",
        ] + audio_map + [
            "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            str(out_seg),
        ]
        run_cmd(cmd)
        return out_seg

    with ThreadPoolExecutor(max_workers=4) as executor:
        rendered_segs = list(executor.map(_render_pip_segment, tasks))

    lines = [f"file '{s.resolve()}'" for s in rendered_segs]
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run_cmd([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        str(final_mp4.resolve()),
    ])
    mix_scene_sfx(timed_spec, final_mp4)


def produce(
    spec_path: Path,
    out_dir: Path,
    fast_enhance: bool = False,
    no_enhancer: bool = False,
    reuse_presenter: Path | None = None,
    skip_tts: bool = False,
    skip_render: bool = False,
    skip_presenter: bool = False,
    skip_compose: bool = False,
    tts_engine: str = "edge",
    speaker: str = "yunjian",
    force_tts: bool = False,
    avatar_image: Path | None = None,
    bgm_enabled: bool = True,
    bgm_path: Path | None = None,
    cpu_workers: int = 4,
    package: bool = False,
    sync: bool = False,
    sync_target: str | None = None,
    course_id: str = "demo",
    entry_id: str | None = None,
    incremental: bool = False,
    force: bool = False,
    course_info: dict | None = None,
    avatar_config: dict | None = None,
    fingerprint: dict | None = None,
    run_qa: bool = True,
    remote_name: str | None = None,
    ) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    timed_spec_file = out_dir / "shots_timed.json"
    voice_wav = out_dir / "voice.wav"
    lecture_mp4 = out_dir / "lecture_courseware.mp4"
    presenter_mp4 = out_dir / "dh.mp4"
    final_mp4 = out_dir / "final.mp4"

    spec = json.loads(Path(spec_path).read_text(encoding="utf-8")) if Path(spec_path).exists() else {}
    if remote_name is None and "-S" in str(spec.get("id", "")):
        sid = str(spec["id"]); slug = re.sub(r"[^a-z0-9]+", "-", str(spec.get("title", "section")).lower()).strip("-")
        remote_name = f"sd_{sid}_{slug}.mp4"
    if incremental or fingerprint is not None:
        from scripts.cache_fingerprint import compute_fingerprint, plan_skips
        current_fp = fingerprint or compute_fingerprint(spec, course_info, avatar_config, root=ROOT)
        auto = plan_skips(
            out_dir,
            current_fp,
            force=force,
            reuse_presenter=bool(reuse_presenter and Path(reuse_presenter).exists()),
        )
        skip_tts = skip_tts or auto["tts"]
        skip_render = skip_render or auto["render"]
        skip_presenter = skip_presenter or auto["presenter"]
        skip_compose = skip_compose or auto["compose"]
        fingerprint = current_fp
        print(f"[cache] skips tts={skip_tts} render={skip_render} presenter={skip_presenter} compose={skip_compose}")

    # Step 1: TTS & Timing
    if skip_tts and timed_spec_file.exists() and voice_wav.exists():
        print(f"[Step 1] Using cached TTS & timing: {timed_spec_file}")
    elif skip_tts:
        print("[Step 1] skip_tts requested but cache missing; running TTS")
        skip_tts = False
    if not skip_tts:
        print(f"[Step 1] Running TTS synthesis ({tts_engine}:{speaker}) and timing measurement...")
        from scripts.build_timed_shots import build_timed_shots
        build_timed_shots(
            spec_path=spec_path,
            output_dir=out_dir,
            engine=tts_engine,
            speaker=speaker,
            force_tts=force_tts,
        )

    # Step 2: HyperFrames Render
    if skip_render and lecture_mp4.exists():
        print(f"[Step 2] Using cached courseware: {lecture_mp4}")
    elif not skip_render:
        print("[Step 2] Rendering HyperFrames headless courseware video...")
        from scripts.render_hyperframes import render_all_shots
        render_all_shots(timed_spec_file, out_dir, max_workers=cpu_workers)

    # Step 3: Presenter Studio (Digital Human)
    if reuse_presenter and Path(reuse_presenter).exists():
        print(f"[Step 3] Reusing existing presenter video: {reuse_presenter}")
        presenter_mp4 = Path(reuse_presenter)
    elif skip_presenter and presenter_mp4.exists():
        print(f"[Step 3] Using cached digital human: {presenter_mp4}")
    elif skip_presenter:
        print("[Step 3] Presenter skipped (GPU stage deferred or cached)")
    else:
        studio = STUDIO or studio_root()
        py = STUDIO_PYTHON or studio_python(studio)
        pipeline_py = (studio / "pipeline.py") if studio else None
        if studio is None or py is None or pipeline_py is None or not pipeline_py.exists():
            print("[Step 3] Presenter Studio not found (set PRESENTER_STUDIO); composing courseware only")
            skip_presenter = True
        else:
            print("[Step 3] Running digital-human pipeline...")
            ryan_image = avatar_image if avatar_image and avatar_image.exists() else default_avatar_image(studio)
            if ryan_image is None:
                raise FileNotFoundError("No avatar image; set course.json avatar.image or assets/avatars/demo.png")
            dh_cmd = [
                str(py), str(pipeline_py),
                "--image", str(ryan_image.resolve()),
                "--audio", str(voice_wav.resolve()),
                "--speaker", speaker,
                "--style", "auto",
                "--out", str(presenter_mp4.resolve()),
            ]
            if no_enhancer:
                dh_cmd.append("--no-enhancer")
            elif fast_enhance:
                dh_cmd.append("--fast-enhance")
            with presenter_gpu_lock():
                run_cmd(dh_cmd, cwd=studio)

    # Step 4: Scene-level 3-tier PiP + SFX + BGM ducking
    if skip_compose and final_mp4.exists():
        print(f"[Step 4] Using cached final mix: {final_mp4}")
    elif skip_compose:
        print("[Step 4] Compose skipped (later stage)")
    else:
        print("[Step 4] Composing per-scene adaptive avatar PiP...")
        if Path(presenter_mp4).exists():
            compose_scene_avatars(timed_spec_file, lecture_mp4, presenter_mp4, final_mp4)
        else:
            print("[Step 4] No presenter video; captions on courseware only")
            compose_lecture_only(timed_spec_file, lecture_mp4, final_mp4, voice=voice_wav)
        if bgm_enabled:
            from scripts.audio_ducking import mix_bgm_ducking
            timed_spec = json.loads(timed_spec_file.read_text(encoding="utf-8")) if timed_spec_file.exists() else spec
            mix_bgm_ducking(final_mp4, spec=timed_spec, bgm_path=bgm_path, enabled=True)

    passed = True
    qa_reports: list[str] = []
    # Step 5: Automated QA Quality Gate
    if run_qa and not skip_compose and final_mp4.exists():
        print("[Step 5] Running Automated QA Inspection...")
        try:
            from scripts.qa_render import run_qa_check
            passed, qa_reports = run_qa_check(
                final_mp4=final_mp4,
                spec_path=spec_path,
                timed_spec_path=timed_spec_file,
            )
            print("\n--- QA REPORT ---")
            for line in qa_reports:
                print(f"  {line}")
            if passed:
                print("  ✅ [QA PASS] Meets 1080x1920, audio, duration, and segmentation standards.")
            else:
                print("  ⚠️ [QA WARNING] QA gate reported warnings/failures.")
        except Exception as e:
            passed = False
            qa_reports = [f"[QA Error] Could not run QA checks: {e}"]
            print(f"  {qa_reports[0]}")

        if package:
            from scripts.package_publisher import package_output
            package_output(
                out_dir,
                spec_path=spec_path,
                course_id=course_id,
                chapter_id=str(entry_id or out_dir.name),
                course_info=course_info,
                final_mp4=final_mp4,
            )

        from scripts.sync_delivery import deliver_after_qa
        deliver_after_qa(
            final_mp4,
            passed=passed,
            reports=qa_reports,
            sync=sync,
            sync_target_name=sync_target or "mac",
            remote_name=remote_name,
        )

    if fingerprint and not skip_compose:
        from scripts.cache_fingerprint import save_cache
        save_cache(out_dir, fingerprint, extra={"final": str(final_mp4)})
    if not skip_compose:
        print(f"\n==========================================")
        print(f"[SUCCESS] Production Complete!")
        print(f"Final MP4: {final_mp4}")
        print(f"==========================================")
    return final_mp4

def main() -> None:
    parser = argparse.ArgumentParser(description="End-to-end vertical lecture video producer")
    parser.add_argument("--course", default="demo", help="Course ID under content/courses/")
    parser.add_argument("--chapter", help="Chapter ID from catalog (e.g. '01' or 'scaling')")
    parser.add_argument("--section", help="Section ID from catalog (e.g. '01-S01')")
    parser.add_argument("--short", help="Short ID from catalog (e.g. '01-redis-read')")
    parser.add_argument("--dir", help="Direct chapter directory")
    parser.add_argument("--spec", help="Direct path to scenes.json (Legacy/V2 mode)")
    parser.add_argument("--out", help="Output directory")
    parser.add_argument("--fast-enhance", action="store_true", help="GFPGAN stride 2 (~2x faster)")
    parser.add_argument("--no-enhancer", action="store_true", help="Disable GFPGAN (default: GFPGAN on)")
    parser.add_argument("--reuse-presenter", help="Path to existing presenter dh.mp4")
    parser.add_argument("--skip-tts", action="store_true", help="Skip TTS if wav/timed json exist")
    parser.add_argument("--tts", default=None, choices=["edge", "qwen"], help="TTS engine (edge/qwen); default from course.json")
    parser.add_argument("--speaker", default=None, help="TTS Speaker name; default from course.json")
    parser.add_argument("--force-tts", action="store_true", help="Force re-synthesizing all TTS audio")
    parser.add_argument("--skip-render", action="store_true", help="Skip HTML recording if lecture_courseware.mp4 exists")
    parser.add_argument("--skip-presenter", action="store_true", help="Skip digital-human if dh.mp4 exists")
    parser.add_argument("--incremental", action="store_true", help="Skip unchanged stages via .cache_fingerprint.json")
    parser.add_argument("--force", action="store_true", help="Ignore incremental cache")
    parser.add_argument("--no-bgm", action="store_true", help="Disable BGM ducking")
    parser.add_argument("--bgm", help="Explicit BGM file path")
    parser.add_argument("--workers", type=int, default=4, help="Playwright HTML render concurrency")
    parser.add_argument("--package", action="store_true", help="Write cover.png and publish_meta.json after QA")
    parser.add_argument("--sync", action="store_true", help="Upload to delivery target after QA pass")
    parser.add_argument("--sync-target", default=None, help="Delivery target name (implies --sync), e.g. mac")
    args = parser.parse_args()

    from scripts.compile_chapter import ChapterCompiler
    compiler = ChapterCompiler(course_id=args.course)
    course_tts = compiler.course_info.get("tts") or {}
    tts_engine = args.tts or course_tts.get("engine") or "edge"
    speaker = args.speaker or course_tts.get("speaker") or "yunjian"
    avatar_rel = (compiler.course_info.get("avatar") or {}).get("image") or ""
    avatar_image = ROOT / avatar_rel if avatar_rel else None

    entry = {"id": "01"}
    if args.chapter or args.short or args.dir or args.section:
        entry, target_dir = compiler.resolve_entry(args.chapter, args.short, args.dir, args.section)
        compiled_spec = compiler.compile_target(
            chapter_id=args.chapter, short_id=args.short, dir_path=args.dir, section_id=args.section
        )
        spec_path = compiled_spec
        if args.out:
            out_dir = Path(args.out)
        else:
            prefix = "ch" if (args.chapter or args.dir) else ("" if args.section else "short_")
            eid = str(entry["id"]).replace("-", "_")
            out_dir = ROOT / "outputs" / f"pipeline_{args.course}_{prefix}{eid}"
    elif args.spec:
        spec_path = Path(args.spec)
        out_dir = Path(args.out) if args.out else ROOT / "outputs" / "pipeline"
    else:
        compiled_spec = compiler.compile_target(chapter_id="01")
        spec_path = compiled_spec
        out_dir = Path(args.out) if args.out else ROOT / "outputs" / f"pipeline_{args.course}_ch01"

    sync = bool(args.sync or args.sync_target)
    produce(
        spec_path=spec_path,
        out_dir=out_dir,
        fast_enhance=args.fast_enhance,
        no_enhancer=args.no_enhancer,
        reuse_presenter=Path(args.reuse_presenter) if args.reuse_presenter else None,
        skip_tts=args.skip_tts,
        skip_render=args.skip_render,
        skip_presenter=args.skip_presenter,
        tts_engine=tts_engine,
        speaker=speaker,
        force_tts=args.force_tts,
        avatar_image=avatar_image,
        bgm_enabled=not args.no_bgm,
        bgm_path=Path(args.bgm) if args.bgm else None,
        cpu_workers=args.workers,
        package=args.package,
        sync=sync,
        sync_target=args.sync_target or "mac",
        course_id=args.course,
        entry_id=str(entry.get("id") or ""),
        incremental=args.incremental,
        force=args.force,
        course_info=compiler.course_info,
        avatar_config=compiler.avatar_config,
    )

if __name__ == "__main__":
    main()
