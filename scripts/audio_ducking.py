#!/usr/bin/env python3
"""BGM library + FFmpeg sidechain audio ducking for the produce pipeline."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BGM_DIR = ROOT / "assets" / "audio" / "bgm"

# Spec §3.4: voice as sidechain, BGM base 35%, ducked ~15% while speaking.
DUCKING_FILTER = (
    "[0:a]asplit=2[voice_main][voice_side];"
    "[1:a]volume=0.35[bgm_base];"
    "[bgm_base][voice_side]sidechaincompress=threshold=0.08:ratio=6:attack=20:release=350[bgm_ducked];"
    "[voice_main][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]"
)

BGM_LIBRARY = {
    "tech_ambient_fast.mp3": "sine=frequency=196:duration=90,tremolo=f=6:d=0.45,aecho=0.6:0.66:40:0.25,volume=0.22",
    "tech_calm_deep.mp3": "anoisesrc=color=brown:duration=90:sample_rate=44100,lowpass=f=180,volume=0.35",
    "upbeat_inspiration.mp3": "sine=frequency=261.63:duration=90,tremolo=f=2:d=0.35,aecho=0.8:0.88:60:0.2,volume=0.16",
}

TEMPLATE_BGM = {
    "algorithm": "tech_ambient_fast.mp3",
    "estimation": "upbeat_inspiration.mp3",
    "system_evolution": "tech_calm_deep.mp3",
    "case_study": "tech_calm_deep.mp3",
    "framework": "tech_calm_deep.mp3",
}


def ducking_filter_complex() -> str:
    return DUCKING_FILTER


def _run(cmd: list[str]) -> None:
    print(f"\n[RUN] {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def ensure_bgm_assets(bgm_dir: Path | None = None) -> dict[str, Path]:
    """Create placeholder BGM files with ffmpeg if the library tracks are missing."""
    target = bgm_dir or BGM_DIR
    target.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for name, lavfi in BGM_LIBRARY.items():
        path = target / name
        if not path.exists() or path.stat().st_size < 1024:
            _run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", lavfi,
                "-codec:a", "libmp3lame", "-b:a", "96k", "-ar", "44100", "-ac", "2",
                str(path),
            ])
        out[name] = path
    return out


def pick_bgm(spec: dict | None = None, template: str | None = None) -> str:
    """Pick a library track from template / scene mood."""
    data = spec or {}
    tmpl = (template or data.get("template") or "").strip()
    if tmpl in TEMPLATE_BGM:
        return TEMPLATE_BGM[tmpl]
    scenes = data.get("scenes") or data.get("shots") or []
    moods = {str(s.get("mood") or "") for s in scenes if isinstance(s, dict)}
    types = {str(s.get("scene_type") or "") for s in scenes if isinstance(s, dict)}
    if "warning" in moods or types & {"naive", "hash_ring", "token_bucket", "sliding_window", "algo_viz"}:
        return "tech_ambient_fast.mp3"
    if types & {"summary", "preview"} or "conclusion" in moods:
        return "upbeat_inspiration.mp3"
    return "tech_calm_deep.mp3"


def mix_bgm_ducking(
    final_mp4: Path,
    spec: dict | None = None,
    bgm_path: Path | None = None,
    enabled: bool = True,
) -> Path:
    """Mix looped BGM under the voice track with sidechain ducking."""
    if not enabled:
        return final_mp4
    if not final_mp4.exists():
        raise FileNotFoundError(f"final video not found: {final_mp4}")

    library = ensure_bgm_assets()
    if bgm_path is None:
        name = pick_bgm(spec)
        bgm_path = library[name]
    elif not bgm_path.exists():
        library = ensure_bgm_assets()
        bgm_path = library.get(bgm_path.name) or next(iter(library.values()))

    tmp = final_mp4.with_name(final_mp4.stem + "_noduck.mp4")
    final_mp4.replace(tmp)
    try:
        _run([
            "ffmpeg", "-y",
            "-i", str(tmp),
            "-stream_loop", "-1", "-i", str(bgm_path),
            "-filter_complex", DUCKING_FILTER,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
            "-shortest",
            str(final_mp4),
        ])
    except subprocess.CalledProcessError:
        print("[BGM] ducking failed, restoring voice-only mix")
        tmp.replace(final_mp4)
        return final_mp4
    tmp.unlink(missing_ok=True)
    print(f"[BGM] sidechain ducking applied with {bgm_path.name}")
    return final_mp4


def mix_from_timed_spec(timed_spec: Path, final_mp4: Path, bgm_path: Path | None = None) -> Path:
    spec = {}
    if timed_spec.exists():
        spec = json.loads(timed_spec.read_text(encoding="utf-8"))
    return mix_bgm_ducking(final_mp4, spec=spec, bgm_path=bgm_path)
