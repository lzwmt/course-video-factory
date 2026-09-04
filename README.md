# 课件视频工厂

**中文** | [English](README.en.md)

把 `chapter.json` + `scenes.json`（或经 `ai_author.py` 的 Markdown）做成 **1080×1920** 竖屏讲解视频：TTS、无头 Chrome、可选数字人画中画、字幕、QA。

公开树是**通用引擎**，只带虚构课 `_demo`。

**相关仓库**：[ai-presenter-studio](https://github.com/lzwmt/ai-presenter-studio)（可选数字人） · 本仓 [course-video-factory](https://github.com/lzwmt/course-video-factory)

## 目录

```text
templates/     视觉配方（系统演进 / 封底估算 / 算法）
assets/        CSS、SVG 拓扑、动效、音效
config/        数字人档位（本地复制 delivery.example.json → delivery.json）
content/courses/_demo/   演示章节
scripts/       编译 → 生产 → QA
```

## 快速开始

```bash
python3 scripts/compile_chapter.py --course demo --chapter 01

# 只要课件、不要数字人
python3 scripts/produce_pipeline.py --course demo --chapter 01 --skip-presenter
```

可选数字人：把 `ai-presenter-studio` clone 成**同级目录**，或：

```bash
export PRESENTER_STUDIO=/path/to/ai-presenter-studio
export PRESENTER_PYTHON=$PRESENTER_STUDIO/.venv/bin/python   # Python 3.12 虚拟环境
```

然后去掉 `--skip-presenter`。权重不进 Git（`bash $PRESENTER_STUDIO/scripts/download_weights.sh`）。默认形象是合成图 `assets/avatars/demo.png`，不是真人。

系统自带的 Python 3.14 加载不了 studio 的 numpy，TTS/Qwen 请用 `PRESENTER_PYTHON`。

本地教材章节留在你机器上；导出公开快照时由 `.gitignore.public` 排除：

```bash
bash scripts/export_public_snapshot.sh
```

## 许可

本工厂原创代码 MIT。第三方见 `NOTICE.md`。数字人相关模型多为**研究向**，商用请自行核对。
