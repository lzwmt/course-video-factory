#!/usr/bin/env python3
"""Automated rendering pipeline for HyperFrames compositions."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
COMPS_DIR = ROOT / "compositions"
CLI = ROOT / "node_modules" / ".bin" / "hyperframes"

def render_single_shot(html_path: Path, output_mp4: Path) -> Path:
    """Render a single HTML composition to MP4 using HyperFrames CLI."""
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    rel_html = html_path.resolve().relative_to(ROOT.resolve())
    rel_out = output_mp4.resolve().relative_to(ROOT.resolve())

    cmd = [
        str(CLI), "render",
        "-c", str(rel_html),
        "-o", str(rel_out),
        "--fps", "30",
        "--quality", "standard"
    ]
    print(f"[*] Rendering shot: {rel_html} -> {rel_out}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)
    return output_mp4

def render_all_shots(timed_spec_file: Path, out_dir: Path, max_workers: int = 4) -> Path:
    """Render all shots and concatenate into unified lecture_courseware.mp4."""
    from scripts.generate_compositions import generate_all_compositions

    # 1. Regenerate compositions from timed spec
    print("[*] Generating HTML compositions...")
    generated_htmls = generate_all_compositions(timed_spec_file)

    # 2. Render each shot in parallel
    shots_out_dir = out_dir / "shots"
    shots_out_dir.mkdir(parents=True, exist_ok=True)

    from concurrent.futures import ThreadPoolExecutor

    def _render_task(html_path: Path) -> Path:
        shot_stem = html_path.stem
        out_mp4 = shots_out_dir / f"{shot_stem}.mp4"
        render_single_shot(html_path, out_mp4)
        return out_mp4

    workers = max(1, int(max_workers))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        shot_mp4s = list(executor.map(_render_task, generated_htmls))
    # 3. Concat all shot videos losslessly
    concat_list = out_dir / "shots_concat.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in shot_mp4s), encoding="utf-8")
    
    lecture_mp4 = out_dir / "lecture_courseware.mp4"
    print(f"[*] Concatenating {len(shot_mp4s)} shots into {lecture_mp4}...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(lecture_mp4)
        ],
        check=True
    )
    print(f"[+] Successfully rendered headless lecture video: {lecture_mp4}")
    return lecture_mp4

if __name__ == "__main__":
    spec_path = ROOT / "data" / "shots_timed.json"
    target_out = ROOT / "outputs" / "pipeline"
    render_all_shots(spec_path, target_out)
