# 通用多课程视频工坊与 AI 编剧系统架构规范 (Universal Course Factory Spec)

**版本**：V5.0 Architecture & Generic Courseware Spec  
**更新日期**：2026-09-02  
**状态**：已落地 / LRU 成片 QA PASS（2026-09-03）  
**代码工程**：`/home/lzwmt/project/system-design-hyperframes`

---

## 一、 建设背景与设计目标

### 1. 现状与痛点
当前工程已全面跑通 Template A（架构拓扑演进）、Template B（封底估算推演）、Template C（算法机制交互）三大视觉模板与数字人画中画混流生产管线。但目前数据结构以《System Design Interview》单课程为核心，存在以下局限：
1. **课程维度硬编码**：全局配置写死在 `content/catalog.json`，无法多课程并行维护与隔离。
2. **讲师与音色写死**：默认使用 Ryan 形象与云希（Yunxi）音色，无法按学科定制讲师画像与主题配色。
3. **内容录入依赖人工排版**：增加新章节需手动编写 `chapter.json` 和 `scenes.json`，缺少直接从原始 Markdown 讲义一键转录的 AI 编剧 Agent。

### 2. V5.0 核心设计目标
* **多课程工作区隔离（Multi-Course Workspace）**：支持无限扩展全新课程（如《LeetCode 高频算法》、《Python 零基础速通》、《AI Agent 原理与实战》、《金融量化与投资估算》等）。
* **课程级元数据与视觉主题解耦（Dynamic Theming & Avatar Binding）**：每个课程独立配置讲师头像、专属 TTS 音色、品牌主题色（Primary Color）与顶部徽章命名。
* **通用 AI 编剧引擎（AI Authoring Agent）**：输入任意 Markdown 笔记，自动识别学科特征、匹配视觉模板、生成符合 DSL 契约的内容包，并自闭环完成校验、修正与一键成片。

---

## 二、 多课程空间架构与目录契约

系统升级为多课程目录树结构，保持向后兼容：

```
content/
├── courses/
│   ├── system-design/                     # 课程 1：系统设计全书（原目录无缝平移）
│   │   ├── course.json                    # 课程元数据、讲师、主题配置
│   │   ├── catalog.json                   # 本课程 28 章及派生 Shorts 索引
│   │   └── chapters/
│   │       ├── 01-scaling/
│   │       ├── 02-estimation/
│   │       ├── 05-consistent-hashing/
│   │       └── ...
│   │
│   ├── leetcode-algorithms/               # 课程 2：LeetCode 经典算法精讲
│   │   ├── course.json
│   │   ├── catalog.json
│   │   └── chapters/
│   │       ├── 01-two-sum/
│   │       ├── 02-lru-cache/
│   │       └── ...
│   │
│   └── python-crash-course/               # 课程 3：Python 核心编程实战
│       ├── course.json
│       ├── catalog.json
│       └── chapters/
│           ├── 01-data-structures/
│           └── ...
```

---

## 三、 课程元数据与个性化配置契约 (`course.json`)

每个课程目录下定义独立的 `course.json`，完全解耦讲师与风格：

```json
{
  "id": "leetcode-algorithms",
  "name": "LeetCode 经典高频算法精讲",
  "instructor": "Ryan",
  "target_audience": "冲刺大厂算法面试的工程师与学生",
  "theme": {
    "primary_color": "#10B981",
    "primary_glow": "rgba(16, 185, 129, 0.25)",
    "bg_color": "#06101E",
    "badge_prefix": "LeetCode 算法精讲"
  },
  "avatar": {
    "image": "assets/avatars/Ryan.png",
    "default_tier": "support",
    "position": "bottom_right"
  },
  "tts": {
    "engine": "edge",
    "speaker": "yunxi",
    "rate": "+0%",
    "pitch": "+0Hz"
  },
  "default_template": "algorithm"
}
```

---

## 四、 通用 AI 编剧 Agent 设计 (`scripts/ai_author.py`)

### 1. CLI 调用契约
```bash
# 从任意 Markdown 讲义一键生成课程内容包并直接渲染成片
python3 scripts/ai_author.py \
  --course "leetcode-algorithms" \
  --chapter "02-lru-cache" \
  --input "docs/raw/lru_cache.md" \
  --produce \
  --send-mac
```

### 2. AI 编剧工作流与自愈机制 (Self-Correction Loop)

```
                       输入 Markdown 讲义
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Stage 1: 学科分析与模板自适应嗅探    │
            │ (代码/数据流 ➔ algorithm,            │
            │  推导/容量 ➔ estimation,            │
            │  分布式/拓扑 ➔ system_evolution)     │
            └──────────────────┬───────────────────┘
                               │
                               ▼
            ┌──────────────────────────────────────┐
            │ Stage 2: 知识分层与口播剧本生成      │
            │ • 提炼 L1 白话 / L2 原理 / L3 考点   │
            │ • 编写 6~8 个分镜口播 (30~45字/分镜) │
            │ • 生成动效 DSL 动作与前端组件数据    │
            └──────────────────┬───────────────────┘
                               │ 输出 chapter.json + scenes.json
                               ▼
            ┌──────────────────────────────────────┐
            │ Stage 3: 编译器静态强校验            │
            │ (scripts/compile_chapter.py)         │
            └──────────┬────────────────┬──────────┘
                       │ 存在错误       │ 校验通过
                       ▼                ▼
            ┌────────────────────┐   ┌──────────────────────────┐
            │ LLM Self-Healing   │   │ Stage 4: 自动推入生产管线 │
            │ 反馈具体校验失败项 │   │ (produce_pipeline.py)    │
            │ 自动重试修复 DSL   │   └──────────────┬───────────┘
            └──────────▲─────────┘                  │
                       │ (最多 3 次)                ▼
                       └────────────         1080×1920 交付成片
```

### 3. LLM API 调用抽象
- **通信协议**：标准 OpenAI SDK 兼容协议（支持 `base_url` 与 `api_key`）。
- **环境凭证绑定**：直接读取系统环境变量 `ANTIGRAVITY_BASE_URL` / `NOAGY_BASE_URL` 与 `ROTATOR_API_KEY`（或自定义 `OPENAI_API_BASE`）。
- **结构化输出保证**：强制启用 `response_format={"type": "json_object"}`，保证 100% 结构合法性。

---

## 五、 渲染与编译管线改造清单

1. **编译器升级 (`scripts/compile_chapter.py`)**：
   - 支持 `--course <course_id>` 参数，自动读取对应课程的 `course.json` 和 `catalog.json`；
   - 支持多课程目录无缝解析，向下兼容现有 `01-scaling` 等既有数据。
2. **HTML 工厂升级 (`scripts/generate_compositions.py`)**：
   - 动态将 `course.json` 中的 `theme.primary_color` 与 `badge_prefix` 注入全局 CSS 变量；
   - 保证不同课程具备独特的品牌视觉调性（如系统设计为深海蓝、LeetCode 为极客绿、Python 为亮橙等）。
3. **管线入口升级 (`scripts/produce_pipeline.py`)**：
   - 支持 `--course <course_id>`，自动按课程指定的头像图片与 TTS 音色进行合成。

---

## 六、 实施与落地路线图 (Sprint Plan)

| 阶段 | 核心任务 | 交付物 |
| :--- | :--- | :--- |
| **Phase 1** | **目录与架构通用化改造** | 建立 `content/courses/` 目录规范，平移现有内容，升级 `compile_chapter.py` 支持 `--course` |
| **Phase 2** | **动态主题与多音色解耦** | 在 `generate_compositions.py` 与 `produce_pipeline.py` 中支持 `course.json` 主题色与数字人/音色动态绑定 |
| **Phase 3** | **开发 `scripts/ai_author.py`** | 实现 LLM 结构化提示词工程、自愈纠错循环（Self-Correction）与一键转录 CLI |
| **Phase 4** | **全流程打通新课程实战出片** | 新建 `leetcode-algorithms` 课程，录入一篇算法 Markdown 并一键全自动生成出片 |
