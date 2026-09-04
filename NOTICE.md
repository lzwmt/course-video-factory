# NOTICE

This repository is a **generic lecture-video factory**. Third-party components keep their own licenses.

## Rendering

- [HyperFrames](https://github.com/heygen-com/hyperframes) — HTML-to-video. See that project's LICENSE.
- GSAP (if loaded by compositions) — GreenSock license; use according to GreenSock terms.

## Optional digital human (`ai-presenter-studio`)

Not bundled. Weights must be downloaded from upstream. Typical stack (research-oriented; **not a commercial grant**):

| Piece | Notes |
|---|---|
| LivePortrait | Official repo + weight license |
| Wav2Lip | Often non-commercial research |
| GFPGAN | Research weights |
| Qwen3-TTS | Qwen / Alibaba license |
| Edge TTS | Cloud API, not redistributable model files |

Do not use other people's likeness without permission. This project is not a deepfake toolkit.

## Content

The public tree ships only `content/courses/_demo/` (original demo copy). Do not add copyrighted textbooks or course notes to public forks unless you have rights.
