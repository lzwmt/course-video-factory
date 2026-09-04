# Contributing

1. Keep **course content** out of PRs unless it is original demo material.
2. Do not commit `outputs/`, weights, portraits, or `config/delivery.json`.
3. New templates belong in `templates/` + `assets/scripts/` with a short spec in `docs/`.
4. Run `python3 scripts/compile_chapter.py --course demo --chapter 01` before sending a pipeline change.
5. Digital-human code lives in a separate repository; this factory should still compile and render with `--skip-presenter`.
