# V3 架构规范与实施方案：内容契约与生产流水线

**日期**：2026-09-02  
**基线提交**：`39179dd`（V2 渲染引擎已冻结）  
**核心原则**：不重做渲染器，不搞黑盒 LLM，不改底层动画代码。**收紧数据契约与职责边界，换章节只换数据。**

---

## 1. 五层职责边界模型

```text
┌───────────────────────────────┐
│ 1. 内容层 (chapter.json)       │ 讲什么：知识点、L1/L2/L3分层、主线/扩展、记忆句
├───────────────────────────────┤
│ 2. 导演层 (scenes.json)        │ 怎么讲：分镜叙事、台词、节点拓扑、动作序列、视觉焦点
├───────────────────────────────┤
│ 3. 规则层 (templates/*.json)   │ 教学法：镜头结构规范 (Hook→Problem→Evolve→Flow→Summary)
│    全局配置 (config/avatar.json)│ 表现力：语义档位 (host / support / pip) 与全局映射
├───────────────────────────────┤
│ 4. 编译层 (compile_chapter.py)│ 编译器：静态强校验 + 契约转换 + 默认值补全
├───────────────────────────────┤
│ 5. 渲染与门禁层 (V2 + QA)      │ 怎么渲染：TTS → Chrome → DH → ASS → FFmpeg ➜ QA 验收
└───────────────────────────────┘
```

---

## 2. 核心数据契约规范

### 2.1 目录索引：`content/catalog.json`
统一单层数组结构，代码统一按 Helper 函数索引，去除结构冗余。

```json
{
  "$schema": "./catalog.schema.json",
  "book": "liquidslr/system-design-notes",
  "chapters": [
    {
      "id": "01",
      "slug": "scaling",
      "title": "从零扩展到百万用户",
      "template": "system_evolution",
      "status": "ready",
      "dir": "content/chapters/01-scaling",
      "target_duration_sec": 57.0
    },
    {
      "id": "02",
      "slug": "estimation",
      "title": "封底估算",
      "template": "estimation",
      "status": "planned",
      "dir": "content/chapters/02-estimation",
      "target_duration_sec": 60.0
    }
  ],
  "shorts": [
    {
      "id": "short-ch1-redis",
      "parent_chapter": "01",
      "title": "Redis 缓存读路径",
      "template": "system_evolution",
      "status": "ready",
      "dir": "content/shorts/01-redis-read",
      "target_duration_sec": 57.0
    }
  ]
}
```

---

### 2.2 知识分层：`content/chapters/01-scaling/chapter.json`
严格执行 L1/L2/L3 知识分层，主线（mainline）决定短视频内容，扩展（extension）保留为后续衍生资产。

```json
{
  "id": "01",
  "title": "从零扩展到百万用户",
  "source": "liquidslr/system-design-notes/01. Scaling",
  "attribution": "liquidslr/system-design-notes · ByteByteGo Vol.1",
  "template": "system_evolution",
  "learning_goal": "理解系统为何被动演进",
  "memory_sentence": "系统设计就是不断解决新的瓶颈",
  
  "concepts": [
    {
      "id": "single_server",
      "name": "单机架构",
      "l1_one_liner": "全部组件挤在一台机器，资源争抢且有单点故障",
      "l2_principle": "Web服务与数据库共享CPU/内存/磁盘IO",
      "l3_engineering": "流量激增时磁盘IO等待过高导致全站雪崩",
      "visual": "single"
    },
    {
      "id": "load_balancer",
      "name": "负载均衡",
      "l1_one_liner": "一台机器扛不住，就让多台一起扛",
      "l2_principle": "LB 反向代理，将请求按算法分发给多个无状态实例",
      "l3_engineering": "健康检查、加权轮询、会话无状态化",
      "visual": "lb"
    },
    {
      "id": "cache",
      "name": "Redis 缓存",
      "l1_one_liner": "能不访问数据库就别访问，高频读拦截在内存",
      "l2_principle": "Cache Aside 模式：先查 Redis，未命中再查 DB 并回写",
      "l3_engineering": "缓存击穿、穿透、雪崩、数据一致性延时双删",
      "visual": "redis"
    },
    {
      "id": "mq",
      "name": "消息队列",
      "l1_one_liner": "能晚点做的事就异步排队，削峰填谷保核心",
      "l2_principle": "生产者快速响应，消费者异步消费",
      "l3_engineering": "消息堆积、重复消费幂等性、死信队列",
      "visual": "mq"
    }
  ],

  "mainline": ["single_server", "load_balancer", "cache", "mq"],
  "extension": ["database_replication", "cdn", "sharding", "resharding"]
}
```

---

### 2.3 语义化数字人配置：`config/avatar.json`
彻底解耦尺寸数值与镜头语义。

```json
{
  "tiers": {
    "host": {
      "name": "主持档",
      "size": 280,
      "position": "center_bottom",
      "description": "开场引导、总结收尾"
    },
    "support": {
      "name": "陪讲档",
      "size": 180,
      "position": "bottom_right",
      "description": "架构拓扑演进、代码展示"
    },
    "pip": {
      "name": "旁白档",
      "size": 140,
      "position": "bottom_left",
      "description": "复杂全链路流转、粒子运动"
    },
    "hidden": {
      "name": "静音/隐藏",
      "size": 0,
      "position": "none",
      "description": "算法纯动画模拟"
    }
  }
}
```

---

### 2.4 教学规则模板：`templates/system_evolution.json`
只定义教学法流程规范与语义策略，不包含任何像素与坐标。

```json
{
  "id": "system_evolution",
  "name": "系统演进型模板 (Template A)",
  "scene_recipe": [
    { "scene_type": "hook",    "default_avatar_tier": "host",    "required": ["narration", "title"] },
    { "scene_type": "problem", "default_avatar_tier": "host",    "required": ["narration", "graph", "actions"] },
    { "scene_type": "evolve",  "default_avatar_tier": "support", "required": ["narration", "graph", "actions"] },
    { "scene_type": "flow",    "default_avatar_tier": "pip",     "required": ["narration", "graph", "actions"] },
    { "scene_type": "summary", "default_avatar_tier": "host",    "required": ["narration", "badge"] }
  ]
}
```

---

### 2.5 导演分镜合同：`content/chapters/01-scaling/scenes.json`
保留 V2 经过实机验证的声明式分镜结构，但数字人改为语义档位 `tier`：

```json
{
  "scenes": [
    {
      "scene": "01",
      "scene_type": "hook",
      "title": "单机为什么会崩？",
      "badge": "系统设计 · 第一章",
      "narration": "单机系统，用户从一百暴增到一万，为什么瞬间瘫痪？",
      "keywords": ["单机", "OVERLOAD"],
      "mood": "warning",
      "avatar_tier": "host",
      "actions": [
        { "type": "counter", "from": 100, "to": 10000, "at": 0.7 },
        { "type": "alert", "level": "danger", "message": "SERVER OVERLOAD", "at": 2.0, "sfx": "error" }
      ]
    },
    {
      "scene": "03",
      "scene_type": "evolve",
      "title": "引入负载均衡",
      "badge": "§4 负载均衡",
      "narration": "在前端挂上负载均衡器，把海量请求均匀分发给后端实例。",
      "keywords": ["负载均衡", "LB"],
      "avatar_tier": "support",
      "graph": {
        "nodes": ["client", "lb", "web", "mysql"],
        "edges": [["client", "lb", "blue"], ["lb", "web", "blue"], ["web", "mysql", "red"]]
      },
      "actions": [
        { "type": "add_node", "id": "lb", "at": 0.8 },
        { "type": "connect", "from": "client", "to": "lb", "at": 1.5 },
        { "type": "connect", "from": "lb", "to": "web", "at": 1.8 }
      ]
    }
  ]
}
```

---

## 3. 编译器定位：`scripts/compile_chapter.py`

坚持“纯编译器”定位，只做三件事：

1. **静态强校验**：
   * 拓扑中的节点必须存在于 `assets/scripts/arch-graph.js` 的 `NODES` 表。
   * 分镜流必须符合 template 的 `scene_recipe` 结构。
   * `attribution` 出处声明字段必须非空。
2. **默认值与语义解析**：
   * 读取 `config/avatar.json`，将 `avatar_tier: "host"` 解析补全为具体渲染器需要的坐标与尺寸 `{ size: 280, position: "center_bottom" }`。
   * 若 `summary` 镜头的 `actions` 未手动声明，自动取 `chapter.json` 中 `concepts[].l1_one_liner` 填装三张要点卡片。
3. **输出中间物**：
   * 导出完全兼容 V2 渲染器的 `compiled_spec.json`。

---

## 4. 生产门禁：`scripts/qa_render.py`

只有通过 QA 的章节，catalog 中的状态才能流转为 `ready`。

```text
[ffprobe & 文件门禁清单]
├── 1. 容器与分辨率: 必须为 1080×1920 MP4
├── 2. 音频轨道: 必须存在 AAC 音频流 (采样率 ≥ 44100Hz, 非全零静音)
├── 3. 时长窗口: actual_duration ∈ [target_duration - 8s, target_duration + 8s]
├── 4. 分镜对齐: 产出的 _pip_segments 数量 === scenes 数量
└── 5. 关键帧无黑屏: 课件视频与成片文件大小均正常 (体积 > 2MB)
```

---

## 5. 验收方案：双用例验证“换数据不改代码”

为验证“换章节不改 Renderer”，V3 必须跑通两个独立用例：

1. **Case A：主线第 1 章演进**
   * 输入：`content/chapters/01-scaling/chapter.json` + `scenes.json`
   * 命令：`python3 scripts/produce_pipeline.py --chapter 01`
   * 验证点：生成全套 8 Scene 演进成片，并通过 `qa_render.py`。

2. **Case B：派生 Shorts 案例（Redis 读路径）**
   * 输入：`content/shorts/01-redis-read/chapter.json` + `scenes.json`
   * 命令：`python3 scripts/produce_pipeline.py --short 01-redis-read`
   * 验证点：**不改动任何 `scripts/*.py` 或 `assets/scripts/*` 代码**，正常编译并产出 57s 成片，通过 QA。
