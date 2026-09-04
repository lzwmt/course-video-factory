#!/usr/bin/env python3
"""Fine-grained dirty-checking fingerprints for the batch produce pipeline.

Hashes (SHA256) written to each chapter output dir as `.cache_fingerprint.json`:
- narration_hash: concatenated scene narrations. Unchanged → skip TTS + digital human.
- visual_hash: scene visual structure + CSS/JS assets. Unchanged → skip HTML recording.
- config_hash: course theme/avatar/TTS + avatar.json + ducking profile. Changed → recompose (Step 4).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CACHE_NAME = ".cache_fingerprint.json"
DUCKING_PROFILE = "sidechaincompress:threshold=0.08:ratio=6:attack=20:release=350:bgm=0.35"

VISUAL_SCENE_KEYS = (
    "scene",
    "scene_type",
    "title",
    "subtitle",
    "badge",
    "keywords",
    "graph",
    "calc_board",
    "assumptions",
    "ladder",
    "array",
    "linked_list",
    "hash_map",
    "tree",
    "stack",
    "dp_table",
    "ring",
    "bucket",
    "sliding_window",
    "code",
    "terminal",
    "actions",
    "graph_hold",
    "preview",
)

VISUAL_ASSET_FILES = (
    "assets/styles/global.css",
    "assets/scripts/arch-graph.js",
    "assets/scripts/calc-board.js",
    "assets/scripts/algo-viz.js",
    "assets/scripts/action-player.js",
    "assets/scripts/motion.js",
    "assets/scripts/gsap.min.js",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _scenes(spec: dict) -> list[dict]:
    items = spec.get("scenes") or spec.get("shots") or []
    return [item for item in items if isinstance(item, dict)]


def narration_payload(spec: dict) -> str:
    parts: list[str] = []
    for scene in _scenes(spec):
        sid = str(scene.get("scene") or scene.get("shot") or scene.get("id") or "")
        narration = scene.get("narration") or scene.get("opening") or ""
        parts.append(f"{sid}\t{narration}")
    return "\n".join(parts)


def visual_payload(spec: dict) -> dict:
    scenes = []
    for scene in _scenes(spec):
        scenes.append({k: scene.get(k) for k in VISUAL_SCENE_KEYS if k in scene})
    return {"scenes": scenes, "template": spec.get("template")}


def asset_hashes(root: Path | None = None) -> dict[str, str]:
    base = root or ROOT
    out: dict[str, str] = {}
    for rel in VISUAL_ASSET_FILES:
        path = base / rel
        out[rel] = sha256_file(path) if path.exists() else "missing"
    return out


def config_payload(
    course_info: dict | None = None,
    avatar_config: dict | None = None,
    extra: dict | None = None,
) -> dict:
    course = course_info or {}
    return {
        "theme": course.get("theme") or {},
        "avatar": course.get("avatar") or {},
        "tts": course.get("tts") or {},
        "avatar_config": avatar_config or {},
        "ducking_profile": DUCKING_PROFILE,
        "extra": extra or {},
    }


def compute_fingerprint(
    spec: dict,
    course_info: dict | None = None,
    avatar_config: dict | None = None,
    root: Path | None = None,
    extra_config: dict | None = None,
) -> dict[str, str]:
    visual = {
        "structure": visual_payload(spec),
        "assets": asset_hashes(root),
    }
    return {
        "narration_hash": sha256_text(narration_payload(spec)),
        "visual_hash": sha256_text(canonical_json(visual)),
        "config_hash": sha256_text(canonical_json(config_payload(course_info, avatar_config, extra_config))),
        "spec_hash": sha256_text(canonical_json(spec)),
    }


def fingerprint_from_files(
    spec_path: Path,
    course_json: Path | None = None,
    avatar_json: Path | None = None,
    root: Path | None = None,
) -> dict[str, str]:
    spec = load_json(spec_path)
    course_info = load_json(course_json) if course_json and course_json.exists() else {}
    avatar_config = load_json(avatar_json) if avatar_json and avatar_json.exists() else {}
    return compute_fingerprint(spec, course_info, avatar_config, root=root)


def cache_path(out_dir: Path) -> Path:
    return Path(out_dir) / CACHE_NAME


def load_cache(out_dir: Path) -> dict:
    path = cache_path(out_dir)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_cache(out_dir: Path, fingerprint: dict, extra: dict | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = dict(fingerprint)
    if extra:
        payload.update(extra)
    path = cache_path(out_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def hashes_match(cached: dict, current: dict, key: str) -> bool:
    old = cached.get(key)
    new = current.get(key)
    return bool(old) and old == new


def plan_skips(
    out_dir: Path,
    current: dict[str, str],
    force: bool = False,
    reuse_presenter: bool = False,
) -> dict[str, bool]:
    """Return skip flags for pipeline stages based on fingerprint + artifacts."""
    out_dir = Path(out_dir)
    timed = out_dir / "shots_timed.json"
    voice = out_dir / "voice.wav"
    lecture = out_dir / "lecture_courseware.mp4"
    presenter = out_dir / "dh.mp4"
    final = out_dir / "final.mp4"

    if force:
        return {
            "tts": False,
            "render": False,
            "presenter": bool(reuse_presenter),
            "compose": False,
            "all": False,
        }

    cached = load_cache(out_dir)
    narration_ok = hashes_match(cached, current, "narration_hash")
    visual_ok = hashes_match(cached, current, "visual_hash")
    config_ok = hashes_match(cached, current, "config_hash")

    skip_tts = narration_ok and timed.exists() and voice.exists()
    skip_render = visual_ok and lecture.exists()
    skip_presenter = (narration_ok and presenter.exists()) or reuse_presenter
    skip_compose = skip_tts and skip_render and skip_presenter and config_ok and final.exists()
    skip_all = skip_compose and narration_ok and visual_ok and config_ok
    return {
        "tts": skip_tts,
        "render": skip_render,
        "presenter": skip_presenter,
        "compose": skip_compose,
        "all": skip_all,
    }
