# 开源计划：通用课件视频工厂（不含教程内容）

## 目标

把本仓库开源成 **通用竖屏讲解视频生产线**（JSON/Markdown → 编译 → Chrome 渲染 → 可选数字人 PiP → 字幕/QA），**不发布** ByteByteGo / system-design-notes / 28 章讲义 / 成片。

数字人工程 `ai-presenter-studio` 作为 **可选第二仓库** 一并开源代码（不含权重、真人脸）。

本地继续用现有 `content/` 生产；公开默认分支只有引擎 + `_demo` 课。

## 非目标

- 不把当前 `.git` 历史原样 push（可能含章节、mp4、绝对路径）。
- 不打包 `pretrained_weights/`、真人肖像、`outputs/`。
- 不宣称 Wav2Lip / GFPGAN / LivePortrait / Qwen TTS 可商用。

## 仓库切分

| 公开仓 | 内容 |
|---|---|
| `course-video-factory`（本仓去内容） | templates、assets 引擎、scripts、config 示例、`content/courses/_demo/` |
| `ai-presenter-studio` | `pipeline.py` + `core/` + 权重下载脚本 + 合成示例脸 |

本地用环境变量连接，不 submodule 绑权重：

- `PRESENTER_STUDIO`
- `PRESENTER_PYTHON`（默认 `$PRESENTER_STUDIO/.venv/bin/python`）

## 阶段 0 — 审计（1 次，阻塞发布）

- 扫两个仓 git 历史：`mp4`、`png` 人像、密钥、`/home/lzwmt`、`content/source`。
- 记录 HyperFrames、GSAP、LivePortrait、Wav2Lip、GFPGAN、Qwen3-TTS、EdgeTTS 的 LICENSE 要点 → `NOTICE.md`。
- 列出必须从公开树删除的路径（见下）。

**公开树禁止出现**

- `content/source/`
- `content/chapters/01-scaling` … `28-*`
- `content/courses/system-design/`（及任何真实课）
- `content/catalog.json` 全书索引（改为只指向 demo）
- `outputs/`、`compositions/`、`dh.mp4`
- 真人 `assets/avatars/*`（可留 `demo.png` 合成图）
- `.pi/`、本机 `delivery.json` 主机名

## 阶段 1 — 去耦合（本仓代码）

1. **路径**：`produce_pipeline.py` / `build_timed_shots.py` 等处的  
   `STUDIO = Path("/home/lzwmt/project/ai-presenter-studio")`  
   改为 env，缺省时允许 `--skip-presenter` 只出课件片。
2. **课程默认**：CLI 默认 `--course demo`，不再默认 system-design。
3. **配置**：`delivery.example.json`；真实 `delivery.json` gitignore。
4. **命名**：`package.json` name/description 改为通用工厂，去掉 “System Design Video Course”。
5. **文档**：README 重写为「从 DSL 出片」；HANDOFF/PROGRESS 中的本机路径与教材引用不进公开树（或大幅删减）。
6. **版权文案**：模板里写死的 `liquidslr · ByteByteGo` 改为 course.json 可选 `attribution` 字段，demo 为空或 “Demo”。

## 阶段 2 — Demo 课（唯一公开内容）

新增 `content/courses/_demo/`（或 `demo/`）：

- `course.json`：虚构主题色、合成脸、edge TTS 占位
- `catalog.json`：1 章
- `chapters/01-counter/`：自写「单机计数器 → 分片」6 镜以内，覆盖 Template A 主路径
- 可选极短 Template B/C 各 1 镜 smoke，证明路由，不讲真题

`.gitignore`：

```
content/source/
content/chapters/
content/courses/*
!content/courses/_demo/
outputs/
compositions/
pretrained_weights/
assets/avatars/*
!assets/avatars/.gitkeep
!assets/avatars/demo.png
.pi/
config/delivery.json
```

本地生产不受影响：真实课程仍在被 ignore 的路径，或继续只存在于本机、不 add。

## 阶段 3 — 数字人仓

- 新 git init 或 filter 历史；`.gitignore`：`pretrained_weights/`、`outputs/`、`.venv/`、真人 png。
- `scripts/download_weights.sh` + checksum，链到官方源。
- README：硬件、研究许可、`--draft`、如何被 factory 调用。
- 禁止未授权深度伪造的 `SECURITY.md` / 使用条款各一段。
- 默认形象：生成脸 `assets/examples/dummy_face.png`。

## 阶段 4 — 许可与文档包

公开根目录：

- `LICENSE`（MIT 或 Apache-2.0，需与 HyperFrames 兼容；若冲突则「引擎自有代码 MIT + 第三方见 NOTICE」）
- `NOTICE.md` 第三方列表
- `README.md` 三步复现：改 demo → compile → produce `--skip-presenter`
- `CONTRIBUTING.md` 简短
- 不把 `docs/raw`、带教材摘录的 spec 全文推上去（UNIVERSAL spec 可改写成无教材名的通用版）

## 阶段 5 — 干净发布

**不要** `git push` 现有历史。推荐：

```text
rsync 引擎 + templates + assets(脚本/样式/sfx) + scripts + demo
→ 空目录 git init → 新 GitHub remote
```

studio 同样新仓。

Checklist 通过再公开：

- [ ] clone 后无 `content/source`、无 28 章、无 mp4
- [ ] `compile_chapter.py --course demo --chapter 01` 过
- [ ] `produce_pipeline.py --skip-presenter` 能出无数字人 mp4（有 Chrome/ffmpeg 的机器）
- [ ] 无 `/home/lzwmt` 字符串
- [ ] LICENSE + NOTICE 在
- [ ] 秘密扫描（gitleaks 或同等）干净

## 风险与取舍

| 风险 | 处理 |
|---|---|
| 教材版权 | 内容根本不进公开树 |
| Wav2Lip 等非商用 | NOTICE + README 写清研究向；factory 可 skip 数字人 |
| 肖像权 | 只用合成脸 |
| HyperFrames 许可 | 保留上游 LICENSE/NOTICE，不伪装自研框架 |
| 误 add 本地课 | gitignore + 发布前 `git ls-files` 人工过目 |

## 建议实施顺序（你确认计划后）

1. 阶段 0 审计清单写入本文件附录（命令输出）
2. 改 env 路径 + skip-presenter
3. 加 `_demo` + gitignore
4. 重写 README / LICENSE / NOTICE
5. 新目录 rsync 试发布，不碰现有 `.git` 直到你明确要换 remote

本地 `system-design-hyperframes` 工作副本保持可出 28 章片；开源是 **导出快照**，不是删掉你的 content。

## 附录 A — 落地记录

- `PRESENTER_STUDIO` / `PRESENTER_PYTHON`：`scripts/presenter_paths.py`；`produce_pipeline.py` 无 studio 时可 `--skip-presenter` 并 `compose_lecture_only`。
- CLI 默认 `--course demo`（compile / produce / batch）。
- Demo：`content/courses/_demo/chapters/01-counter/`（自写计数器分片）。
- 许可：`LICENSE` MIT、`NOTICE.md`、`CONTRIBUTING.md`、`SECURITY.md`、`config/delivery.example.json`。
- 导出：`bash scripts/export_public_snapshot.sh` → `dist/oss-snapshot`（gitignore.public 去掉 source/28 章/成片）。
- 校验：`python3 tests/test_demo_compile.py` PASS；snapshot 无 `content/source` / `01-scaling`。
- 数字人仓：`scripts/download_weights.sh`、`assets/examples/dummy_face.png`、`.gitignore` 权重、`SECURITY.md`。
- **未做**：不 `git push`、不 `filter-repo` 现有历史、不跑全链路 Chrome 出片（需本机 HyperFrames/ffmpeg 时长）。

