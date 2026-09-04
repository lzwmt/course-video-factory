#!/usr/bin/env python3
"""Batch scheduler with incremental fingerprints and mixed CPU/GPU workers."""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class ProduceJob:
    kind: str  # chapter | short
    entry_id: str
    title: str
    spec_path: Path
    out_dir: Path
    skips: dict[str, bool] = field(default_factory=dict)
    fingerprint: dict = field(default_factory=dict)
    final_mp4: Path | None = None
    error: str | None = None


def default_out_dir(course_id: str, kind: str, entry_id: str) -> Path:
    prefix = "ch" if kind == "chapter" else "short_"
    eid = str(entry_id).replace("-", "_")
    return ROOT / "outputs" / f"pipeline_{course_id}_{prefix}{eid}"


def ready_entries(compiler, include_chapters: bool = True, include_shorts: bool = True) -> list[tuple[str, dict]]:
    items: list[tuple[str, dict]] = []
    if include_chapters:
        for ch in compiler.catalog.get("chapters") or []:
            if ch.get("status") == "ready":
                items.append(("chapter", ch))
    if include_shorts:
        for sh in compiler.catalog.get("shorts") or []:
            if sh.get("status") == "ready":
                items.append(("short", sh))
    return items


def build_jobs(
    compiler,
    course_id: str,
    force: bool,
    reuse_presenter: Path | None,
    only_ids: set[str] | None = None,
) -> list[ProduceJob]:
    from scripts.cache_fingerprint import compute_fingerprint, plan_skips

    avatar_cfg = compiler.avatar_config
    jobs: list[ProduceJob] = []
    for kind, entry in ready_entries(compiler):
        eid = str(entry.get("id"))
        if only_ids and eid not in only_ids and str(entry.get("slug") or "") not in only_ids:
            continue
        if kind == "chapter":
            spec_path = compiler.compile_target(chapter_id=eid)
        else:
            spec_path = compiler.compile_target(short_id=eid)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        out_dir = default_out_dir(course_id, kind, eid)
        fp = compute_fingerprint(spec, compiler.course_info, avatar_cfg, root=ROOT)
        skips = plan_skips(out_dir, fp, force=force, reuse_presenter=bool(reuse_presenter))
        jobs.append(ProduceJob(
            kind=kind,
            entry_id=eid,
            title=str(entry.get("title_zh") or entry.get("title") or eid),
            spec_path=spec_path,
            out_dir=out_dir,
            skips=skips,
            fingerprint=fp,
        ))
    return jobs


def _produce_kwargs(job: ProduceJob, args, compiler, skip_override: dict[str, bool] | None = None) -> dict:
    skips = dict(job.skips)
    if skip_override:
        skips.update(skip_override)
    avatar_rel = (compiler.course_info.get("avatar") or {}).get("image") or ""
    avatar_image = ROOT / avatar_rel if avatar_rel else None
    reuse = Path(args.reuse_presenter) if args.reuse_presenter else None
    do_package = not args.no_package
    if skip_override and "package" in skip_override:
        do_package = bool(skip_override["package"]) and not args.no_package
    inner_workers = 1 if skip_override else max(1, int(args.workers))
    return dict(
        spec_path=job.spec_path,
        out_dir=job.out_dir,
        fast_enhance=args.fast_enhance,
        reuse_presenter=reuse,
        skip_tts=skips.get("tts", False),
        skip_render=skips.get("render", False),
        skip_presenter=skips.get("presenter", False),
        skip_compose=skips.get("compose", False),
        tts_engine=args.tts_engine,
        speaker=args.speaker,
        force_tts=args.force,
        avatar_image=avatar_image,
        bgm_enabled=not args.no_bgm,
        cpu_workers=inner_workers,
        package=do_package,
        sync=args.sync and do_package,
        sync_target=args.sync_target,
        course_id=args.course,
        entry_id=job.entry_id,
        incremental=False,
        force=args.force,
        course_info=compiler.course_info,
        avatar_config=compiler.avatar_config,
        fingerprint=job.fingerprint,
        run_qa=do_package or not (skip_override or {}).get("compose", False),
    )


def run_batch(args) -> list[ProduceJob]:
    from scripts.compile_chapter import ChapterCompiler
    from scripts.produce_pipeline import produce

    compiler = ChapterCompiler(course_id=args.course)
    course_tts = compiler.course_info.get("tts") or {}
    args.tts_engine = args.tts or course_tts.get("engine") or "edge"
    args.speaker = args.speaker or course_tts.get("speaker") or "yunxi"

    only_ids = None
    if args.chapter:
        only_ids = {item.strip() for item in args.chapter.split(",") if item.strip()}
    jobs = build_jobs(
        compiler,
        args.course,
        force=args.force,
        reuse_presenter=Path(args.reuse_presenter) if args.reuse_presenter else None,
        only_ids=only_ids,
    )
    if not jobs:
        print(f"[batch] no ready chapters/shorts for course {args.course}")
        return []

    cpu_n = max(1, int(args.workers))
    print(f"[batch] {len(jobs)} job(s), CPU workers={cpu_n}, GPU queue=1, incremental={not args.force}")
    for job in jobs:
        print(f"  - {job.kind} {job.entry_id} {job.title} skips={job.skips}")

    def run_job(job: ProduceJob, skip_override: dict[str, bool]) -> ProduceJob:
        try:
            kwargs = _produce_kwargs(job, args, compiler, skip_override)
            job.final_mp4 = produce(**kwargs)
        except Exception as exc:  # noqa: BLE001
            job.error = str(exc)
            print(f"[batch] FAIL {job.kind} {job.entry_id}: {exc}")
        return job

    # Stage A: CPU-heavy TTS + Playwright HTML (skip GPU + compose)
    cpu_jobs = [j for j in jobs if not (j.skips.get("tts") and j.skips.get("render"))]
    if cpu_jobs:
        print(f"[batch] Stage A CPU pool: {len(cpu_jobs)} job(s)")
        with ThreadPoolExecutor(max_workers=cpu_n) as pool:
            futs = [
                pool.submit(run_job, job, {"presenter": True, "compose": True, "package": False})
                for job in cpu_jobs
            ]
            for fut in as_completed(futs):
                fut.result()
        failed = [j for j in cpu_jobs if j.error]
        if failed:
            print(f"[batch] Stage A failures: {[j.entry_id for j in failed]}")

    # Stage B: GPU presenter serial queue (mutex also inside produce)
    gpu_jobs = [j for j in jobs if not j.skips.get("presenter") and not j.error]
    print(f"[batch] Stage B GPU queue: {len(gpu_jobs)} job(s)")
    for job in gpu_jobs:
        run_job(job, {"tts": True, "render": True, "compose": True, "package": False})

    # Stage C: compose + ducking + QA + package (+ optional sync)
    compose_jobs = [j for j in jobs if not j.skips.get("all") and not j.error]
    if compose_jobs:
        print(f"[batch] Stage C compose/QA: {len(compose_jobs)} job(s)")
        with ThreadPoolExecutor(max_workers=cpu_n) as pool:
            futs = [
                pool.submit(run_job, job, {"tts": True, "render": True, "presenter": True})
                for job in compose_jobs
            ]
            for fut in as_completed(futs):
                fut.result()

    print("\n========== BATCH SUMMARY ==========")
    for job in jobs:
        state = "ERROR" if job.error else ("CACHED" if job.skips.get("all") else "DONE")
        print(f"  [{state}] {job.kind} {job.entry_id} -> {job.out_dir / 'final.mp4'}")
        if job.error:
            print(f"           {job.error}")
    print("===================================")
    return jobs


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch produce all ready chapters/shorts")
    parser.add_argument("--course", default="demo")
    parser.add_argument("--all", action="store_true", help="Produce every ready chapter and short")
    parser.add_argument("--incremental", action="store_true", help="Skip unchanged stages (default)")
    parser.add_argument("--force", action="store_true", help="Ignore cache and rerun all stages")
    parser.add_argument("--chapter", help="Comma-separated chapter/short ids to limit the batch")
    parser.add_argument("--workers", type=int, default=int(os.environ.get("HF_CPU_WORKERS", "4")))
    parser.add_argument("--reuse-presenter", help="Reuse an existing dh.mp4 for all jobs")
    parser.add_argument("--fast-enhance", action="store_true")
    parser.add_argument("--tts", choices=["edge", "qwen"])
    parser.add_argument("--speaker")
    parser.add_argument("--sync", action="store_true", help="Upload after QA pass")
    parser.add_argument("--sync-target", default="mac")
    parser.add_argument("--no-bgm", action="store_true")
    parser.add_argument("--no-package", action="store_true")
    args = parser.parse_args()
    if not (args.all or args.incremental or args.chapter or args.force):
        parser.error("specify --all, --incremental, --chapter, or --force")
    run_batch(args)


if __name__ == "__main__":
    main()
