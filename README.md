# Course Video Factory

Turn `chapter.json` + `scenes.json` (or Markdown via `ai_author.py`) into **1080×1920** lecture videos: TTS, headless Chrome, optional digital-human PiP, captions, QA.

This public tree is a **generic engine**. Only the fictional `_demo` course is included.

## Layout

```text
templates/     visual recipes (system evolution / estimation / algorithm)
assets/        CSS, SVG graph, motion, SFX
config/        avatar tiers (copy delivery.example.json → delivery.json locally)
content/courses/_demo/   original demo chapter
scripts/       compile → produce → qa
```

## Quick start

```bash
python3 scripts/compile_chapter.py --course demo --chapter 01

# Courseware only (no digital human)
python3 scripts/produce_pipeline.py --course demo --chapter 01 --skip-presenter
```

Optional digital human: clone `ai-presenter-studio` as a **sibling directory**, or set:

```bash
export PRESENTER_STUDIO=/path/to/ai-presenter-studio
export PRESENTER_PYTHON=$PRESENTER_STUDIO/.venv/bin/python   # Python 3.12 venv
```

Then omit `--skip-presenter`. Weights stay outside git (`bash $PRESENTER_STUDIO/scripts/download_weights.sh`). Default portrait is `assets/avatars/demo.png` (synthetic), not a real person.

System Python 3.14 cannot load the studio numpy wheel; use `PRESENTER_PYTHON` for TTS/Qwen as well.

Local textbook chapters stay on your machine; they are excluded by `.gitignore.public` when you export a snapshot:

```bash
bash scripts/export_public_snapshot.sh
```

## License

MIT for this factory's original files. Third-party terms: `NOTICE.md`. Digital-human models are typically **research-only**; commercial use is your problem.
