# 全自动化批处理与多平台发布流水线规范 (Batch & Publish Pipeline Spec)

**版本**：V6.0 Automated Production & Publishing Specification  
**更新日期**：2026-09-04  
**适用范围**：
- 《系统设计面试通关课》（`system-design`）及后续所有多课程体系
- 全链路批量视频生成、增量脏检查渲染、多平台发布素材打包与远程自动交付

---

## 一、 设计目标与架构全景

### 1. 核心目标
1. **一键批量生产（One-Click Batching）**：支持单指令触发整门课程（全章节 + Shorts）流水线编译、合成与渲染，无需人工逐章触发。
2. **细粒度增量脏检查缓存（Smart Caching）**：精准比对分镜文本、视觉结构与样式变更，仅重跑受影响的管道环节，单章更新渲染缩短至 20 秒以内。
3. **发布就绪一体化（Zero-Effort Publishing）**：自动提取高清封面图、提取视频分段章节时间戳、生成各大主流社媒平台（B站/小红书/抖音/视频号）发布元数据包。
4. **设备间自动推流同步（Auto-Delivery & Hooks）**：生产完毕后自动通过网络同步至目标设备（如 Mac `~/Downloads/` 或 NAS），并支持 Webhook 通知。
5. **视听沉浸感质感提升（Audio Ducking）**：引入环境背景音乐（BGM），口播发声时自动闪避（Ducking），提升短视频视听体验。

---

## 二、 系统架构与流程总览

```
                        catalog.json (课程大纲目录)
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │   1. 批量调度与增量缓存器 (scripts/batch_produce.py)    │
       └────────────────────────────┬───────────────────────────┘
                                    │
             ┌──────────────────────┴──────────────────────┐
             ▼                                             ▼
       [已缓存/无变更]                              [脏数据/需重跑]
       跳过相应阶段                                   阶段化精准重渲
             │                                             │
             │                               ┌─────────────┴─────────────┐
             │                               ▼                           ▼
             │                        [Stage A: CPU 密集]        [Stage B: GPU 密集]
             │                       Playwright HTML 并发渲染    Presenter 数字人串行队列
             │                               └─────────────┬─────────────┘
             │                                             │
             └──────────────────────┬──────────────────────┘
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │   2. 视听混流与 QA 门禁 (Audio Ducking & QA Gate)        │
       │   - 3-Tier PiP 画中画融合                               │
       │   - BGM 智能闪避 (Sidechain Ducking)                    │
       │   - 自动化 QA 门禁校验 (1080x1920 / 音视频对齐)          │
       └────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │   3. 发布包工厂 (scripts/package_publisher.py)          │
       │   - 自动生成高清封面图 (cover.png)                       │
       │   - 自动提取章节时间戳 (Chapter Markers)                │
       │   - 平台专属标题/简介/标签元数据 (publish_meta.json)      │
       └────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │   4. 远端同步与通知 (Remote Sync & Webhook)             │
       │   - SCP / Rsync 自动推流至 Mac ~/Downloads/            │
       │   - 飞书 / 企微 Webhook 质检报告推送                    │
       └────────────────────────────────────────────────────────┘
```

---

## 三、 四大核心模块契约与实现细节

### 模块 1：批量调度与增量缓存系统 (`scripts/batch_produce.py`)

#### 1. 命令行交互规范
```bash
# 批量生产指定课程的所有章节与短视频
python scripts/batch_produce.py --course system-design --all

# 仅生产未生成或有变更的章节（默认启用增量缓存）
python scripts/batch_produce.py --course system-design --incremental

# 强制重跑全流程（忽略缓存）
python scripts/batch_produce.py --course system-design --all --force
```

#### 2. 阶段化哈希脏检查（Fine-grained Dirty Checking）
在每个章节输出目录下维护 `.cache_fingerprint.json`：
* **`narration_hash`**：所有分镜的 `narration` 拼接 SHA256。若无变更，**跳过 Step 1 (TTS) 与 Step 3 (数字人合成)**。
* **`visual_hash`**：分镜结构（`graph`, `calc_board`, `array`, `linked_list`, `actions` 等）与 `global.css`/JS 脚本 SHA256。若无变更，**跳过 Step 2 (课件 HTML 录制)**。
* **`config_hash`**：`course.json` 主题、Avatar 配置变更。若变更，触发快速重新合成（Step 4）。

#### 3. 混合并发调度器
* **CPU Worker Pool (Playwright)**：根据主机 CPU 核心数并发运行多个 Shot HTML 录制任务（默认 4 进程）。
* **GPU Single Worker Queue (Presenter Studio)**：使用互斥锁限制同时只能运行 1 个数字人推理任务，避免 GPU 显存溢出（OOM）。

---

### 模块 2：多平台发布素材打包与封面工厂 (`scripts/package_publisher.py`)

#### 1. 高清封面图自动提取与增强 (`cover.png`)
* **提取源**：自动截取分镜 00 或封面镜头的黄金帧（默认 `t = 1.5s`）。
* **分辨率**：标准 1080×1920 竖屏 PNG。
* **自动合成元素**：叠加课程主题 Badge 角标、章节标题大字、重点关键词高亮条。

#### 2. 多平台元数据结构 (`publish_meta.json`)
```json
{
  "course_id": "system-design",
  "chapter_id": "01",
  "title": "从零扩展到百万用户：高并发架构演进全流程",
  "durations": 79.5,
  "platforms": {
    "bilibili": {
      "title": "【系统设计】百万用户高并发架构如何一步步演进？",
      "tags": ["系统设计", "高并发", "架构师", "后端开发", "面试"],
      "desc": "本期讲解架构从单机演进至分布式全过程。\n\n时间轴：\n00:00 痛点引入\n00:25 单机瓶颈\n01:10 数据库读写分离\n02:00 缓存引入\n02:45 总结复盘",
      "cover": "cover_bilibili.png"
    },
    "xiaohongshu": {
      "title": "大厂架构面试必考！百万并发系统演进图解 🔥",
      "tags": ["#程序员", "#系统设计", "#架构设计", "#后端面试", "#技术分享"],
      "desc": "面试官问你'系统如何支撑百万DAU'，千万别直接上K8s微服务！记住这套标准化演进路径..."
    },
    "douyin": {
      "title": "系统设计通关课 01：单机到百万架构演进 #程序员 #系统设计 #计算机",
      "tags": ["系统设计", "后端开发", "程序员"]
    }
  },
  "chapter_markers": [
    { "time": "00:00", "title": "痛点引入" },
    { "time": "00:25", "title": "单机数据库瓶颈" },
    { "time": "01:10", "title": "读写分离架构" }
  ]
}
```

---

### 模块 3：自动化远端同步与事件钩子 (`scripts/sync_delivery.py`)

#### 1. 交付目标配置 (`config/delivery.json`)
```json
{
  "targets": {
    "mac": {
      "type": "scp",
      "host": "mac",
      "remote_dir": "~/Downloads/",
      "auto_sync": true
    },
    "nas": {
      "type": "rsync",
      "destination": "nas:/volume1/videos/hyperframes/",
      "auto_sync": false
    }
  },
  "webhooks": [
    {
      "name": "feishu",
      "url": "${FEISHU_WEBHOOK_URL}",
      "notify_on": ["pass", "fail"]
    }
  ]
}
```

#### 2. 流水线挂载点
在 `produce_pipeline.py` 的 Step 5 QA 质检通过后，自动调用同步钩子，若开启 `--sync` 则静默推送，并在终端打印绿色传输状态。

---

### 模块 4：视听沉浸感打磨与 BGM 智能闪避 (Audio Ducking)

#### 1. 背景音乐库归档 (`assets/audio/bgm/`)
* `tech_ambient_fast.mp3`（快节奏推演，适合算法与代码题）
* `tech_calm_deep.mp3`（沉浸式深色科技感，适合大架构与系统演进）
* `upbeat_inspiration.mp3`（励志通关感，适合总结与实战）

#### 2. FFmpeg Sidechain Audio Ducking 滤镜链
```bash
# 语音作为主控信号，BGM 自动闪避滤镜规范
[0:a]asplit=2[voice_main][voice_side]; \
[1:a]volume=0.35[bgm_base]; \
[bgm_base][voice_side]sidechaincompress=threshold=0.08:ratio=6:attack=20:release=350[bgm_ducked]; \
[voice_main][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[aout]
```
* **效果**：数字人说话时，BGM 音量平滑降至约 15%（背景衬托）；口播停顿和分镜切换间隔，BGM 平滑上浮至 35%，消除冷场。

---

## 四、 实施计划与里程碑 (Milestones)

| 阶段 | 事项描述 | 产出成果 | 负责人 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **BGM 智能闪避引擎落地** | `produce_pipeline.py` 集成 sidechain ducking 与 BGM 库 | Pipeline Agent |
| **Phase 2** | **批量调度与增量缓存器** | `scripts/batch_produce.py`（支持 `--course ... --all` 与三级哈希缓存） | Batch Agent |
| **Phase 3** | **发布包与封面工坊** | `scripts/package_publisher.py`（生成 `cover.png` 与 `publish_meta.json`） | Publisher Agent |
| **Phase 4** | **远程自动同步与全链路闭环** | 集成 `--sync-target mac` 自动推流与多章节全自动化验证 | E2E Agent |
