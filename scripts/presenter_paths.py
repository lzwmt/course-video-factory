#!/usr/bin/env python3
"""Resolve optional AI Presenter Studio without machine-specific paths."""
from __future__ import annotations

import os
from pathlib import Path

FACTORY_ROOT = Path(__file__).resolve().parent.parent


def studio_root() -> Path | None:
    env = os.environ.get("PRESENTER_STUDIO", "").strip()
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.append(FACTORY_ROOT.parent / "ai-presenter-studio")
    for p in candidates:
        if (p / "pipeline.py").is_file():
            return p.resolve()
    return None


def studio_python(root: Path | None = None) -> Path | None:
    env = os.environ.get("PRESENTER_PYTHON", "").strip()
    if env:
        return Path(env).expanduser()
    root = root or studio_root()
    if root is None:
        return None
    venv_py = root / ".venv" / "bin" / "python"
    return venv_py if venv_py.exists() else Path("python3")


def studio_site_packages(root: Path | None = None) -> Path | None:
    root = root or studio_root()
    if root is None:
        return None
    venv_lib = root / ".venv" / "lib"
    if not venv_lib.exists():
        return None
    for site in sorted(venv_lib.glob("python*/site-packages")):
        if site.is_dir():
            return site
    return None


def default_avatar_image(root: Path | None = None) -> Path | None:
    root = root or studio_root()
    factory_demo = FACTORY_ROOT / "assets" / "avatars" / "demo.png"
    if factory_demo.exists():
        return factory_demo
    if root is None:
        return None
    for rel in (
        "assets/examples/dummy_face.png",
        "assets/Ryan.png",
    ):
        p = root / rel
        if p.exists():
            return p
    return None
