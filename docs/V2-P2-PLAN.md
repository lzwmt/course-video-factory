# V2 P2 迭代计划

**日期**：2026-09-01  
**基线成片**：`outputs/pipeline_v2_p1/final.mp4`（8 Scene，56.6s）  
**验收成片**：`outputs/pipeline_v2_p2/final.mp4` → Mac `~/Downloads/final_v2_p2.mp4`  
**原则**：不搬家 `/video-engine`、不加 LLM 导演、不加 Browser/CDP。总时长锁 **55–58s**。不为炫技加镜。

对照总规：[`docs/V2-ITERATION.md`](V2-ITERATION.md) §5.1 / §6 P2。

---

## 1. P2 要解决什么

P1 已经有：三区布局、SVG 拓扑、粒子、数字人三档。  
P1 还缺的是 **导演运行时**：坐标和 timeline 仍手写在 `generate_compositions.py`；`actions[]` 只是注释；`zoom` 未上场；底栏 350px 空着；没有「证明」镜头。

P2 把「课件生成器」再推一步，变成 **同一条 60s 片可声明式重放的导演器**。

```text
ch1-v2-scenes.json
  graph: { nodes, edges }     → arch-graph 拼 SVG
  actions: [connect, packet…]  → motion.js 编 timeline
  captions / keywords          → 底栏字幕（避开 PiP）
  可选 code 2–3s               → Cache Aside 证明，不另开长镜
```

---

## 2. 范围

### 做（按顺序，不可并行乱插）

| 序 | 项 | Must / Opt | 说明 |
|---|---|---|---|
| 1 | SVG 节点库 | Must | 坐标离开生成器 |
| 2 | `actions[]` 驱动动画 | Must | JSON → GSAP |
| 3 | zoom/focus 各至少一次 | Must | Scene 02 瓶颈 + Scene 05 Redis 或 Scene 07 流 |
| 4 | 底栏关键词字幕 | Must | 句级 + 关键词，避开数字人 |
| 5 | Code **或** Terminal 证明镜 | Must（二选一，推荐 Code） | 塞进现有 Scene 05，不新增第 9 镜 |
| 6 | 情绪最小集 + SFX | Opt | 画面告警联动优先；SFX 各事件最多 1 次 |

### 不做

- 全量 `ch1-full-shots.json`
- Browser Scene / CDP
- 词级时间戳（Edge 不稳则句级即可）
- 改 `ai-presenter-studio/composer.py`（继续本仓 ffmpeg 三档）
- BGM、PPT 转场、数字人 LivePortrait style 大改

---

## 3. 时长预算（硬约束）

当前 8 镜合计 **≈56.6s**，口播已贴 57s 目标。P2 **禁止**再加独立长 Scene。

| 策略 | 决策 |
|---|---|
| Code 证明 | **内嵌 Scene 05**（Redis）后半 2–3s：上半拓扑 + HIT 粒子，下半 6–8 行 Cache Aside；口播不改或只加半句「命中就直接返回」 |
| Terminal | 仅当 Code 做不进去时，用 Scene 07 右侧小窗 `curl` 延迟对比，≤2s |
| 字幕 | 不占口播时间，合成阶段烧 ASS |
| zoom | 吃现有 duration，0.5–0.8s，不延长 TTS |

若测时回退超 58s：砍 Code 行数或砍 Scene 08 CTA 半句，**不砍演进逻辑**。

---

## 4. 任务拆解

### P2-1 抽出 SVG 节点库

**新文件** `assets/scripts/arch-graph.js`（渲染时与 `motion.js` 一并引入；HTML 组件可选 `compositions/components/arch-graph` 仅作文档）。

节点固定坐标系（viewBox `0 0 936 560`，与 P1 一致，避免重排闪烁）：

| id | 角色 | 用途 |
|---|---|---|
| client | Client | 全图 |
| lb | Load Balancer | 04+ |
| web | Web Cluster | 03+ |
| redis | Redis Cache | 05+ |
| mysql | MySQL | 03+ |
| mq | Message Queue | 06+ |
| worker | Worker | 06+ |
| single | Single Server | 仅 02 |

生成器只传：

```json
"graph": {
  "nodes": ["client", "lb", "web", "redis", "mysql"],
  "edges": [
    ["client", "lb", "blue"],
    ["lb", "web", "blue"],
    ["web", "redis", "green"],
    ["web", "mysql", "red"]
  ]
}
```

`arch-graph.mount("#topo", graph)` 画节点/边；边 id 规则 `e-{from}-{to}`。坐标表只存在这一处。

**完成定义**：`generate_compositions.py` 中无 `NODE_DEFS` / 手写 `x,y`。

### P2-2 `actions[]` 真正驱动动画

扩展（不破坏现有字段）`data/ch1-v2-scenes.json`：

| type | 参数 | 映射 |
|---|---|---|
| enter | `target` | `motion.enter` |
| connect | `from`, `to` | `motion.connect("#e-from-to")` |
| packet | `from`, `to`, `color`, `label?` | 节点中心点查表 → `motion.packet` |
| highlight | `target`, `tag?` | 节点 glow |
| metric | `target`, `value` | CPU/IO 条 |
| counter | `from`, `to` | Hook 计数 |
| alert | `message` | OVERLOAD |
| zoom | `target`, `scale` | camera |
| focus | `target` | 其它节点降透明 |
| code_line | `index` | Code 行高亮 |

生成器输出 **一份解释器**，写入每镜 HTML：

```js
playActions(tl, scene.actions, ArchGraph.centers);
```

手搓 timeline 只允许 Hook 计数曲线、Summary 卡片错峰这两处例外。

**完成定义**：Scene 03–07 的粒子/连线/高亮全部来自 JSON，改 JSON 重渲即变，不必改 Python 字符串。

### P2-3 Camera zoom / focus

挂点（各一次，禁止每镜都 zoom）：

1. **Scene 02 Problem**：CPU 打满后 `zoom` 到 `#node-single`（scale ≤ 1.12，0.6s），体现瓶颈。  
2. **Scene 05 Cache**：Redis 出现后 `focus("#node-redis")` + 轻 zoom；或 **Scene 07** HIT 粒子到达 Redis 时 focus。

实现注意（P1 闪烁教训）：

- 只 transform `#topo`，不对 `.node-box` 开 CSS `transition`
- `gsap.config({ force3D: false })` 保持
- SVG opacity 继续走 `attr`

**完成定义**：成片里肉眼能数出 ≥1 次放大到 Redis 或单机箱，且放大后不再闪。

### P2-4 底栏关键词字幕

布局（350px 底栏内）：

```text
字幕条：水平居中，Bottom 48–90px
数字人 host/center：字幕上移到 overlay 上方（MarginV ≈ 360）或改左对齐短句
数字人 side/右下：字幕居中偏左
数字人 pip/左下：字幕居中偏右
```

内容：

- 主行：该 Scene `narration` 按句切开（`，。`）
- 关键词行：Scene 级 `keywords: ["Redis", "80% HIT"]`，主色 `--color-primary`

实现：`scripts/build_captions.py` 读 timed JSON → ASS；`compose_scene_avatars` 每段 `-vf ass=`。无词级时间戳则按字符占比均分（与现 SRT 逻辑同类）。

**完成定义**：8 段都有字幕；无遮挡人脸；关键词在 05/06/07 可见。

### P2-5 证明镜头（推荐 Code，不做两条）

**Scene 05 内嵌**，不新增 scene_type 也可：

```text
核心区上 70%：arch-graph（LB/Web/Redis/MySQL）
下 30%：6–8 行伪代码
```

```text
get(key):
  v = redis.get(key)
  if v: return v          # HIT
  v = db.query(key)       # MISS
  redis.set(key, v)
  return v
```

`code_line` action 随口播「拦截百分之八十」高亮 `if v` 行。

Terminal 作为备选：仅 Scene 07 小窗两行延迟数字，**P2 默认不做 Terminal**，避免双证明挤时长。

**完成定义**：成片 Redis 段能读到 Cache Aside 关键行；全片仍 ≤58s。

### P2-6 可选：情绪 + SFX

- 情绪先 **画面**：`avatar.mood` 或旁白规则 → 节点/字幕色（warning=红，conclusion=蓝）。不改 LivePortrait。
- SFX 最多 3 个点：Hook OVERLOAD、Scene 05 HIT、Scene 02 CPU 满。音量 10–20%。无素材则跳过，不阻塞验收。

---

## 5. 文件改动图

| 路径 | 动作 |
|---|---|
| `assets/scripts/arch-graph.js` | **新建** 节点库 + centers |
| `assets/scripts/motion.js` | 补 `focus`；packet 走 centers |
| `assets/scripts/action-player.js` | **新建** JSON actions → timeline |
| `assets/styles/global.css` | code 行、字幕安全区 class |
| `data/ch1-v2-scenes.json` | `graph` / 补齐 actions / `keywords` |
| `scripts/generate_compositions.py` | 瘦身为壳：header + mount graph + playActions |
| `scripts/build_captions.py` | **新建** ASS |
| `scripts/produce_pipeline.py` | 烧字幕；out `outputs/pipeline_v2_p2/` |
| `scripts/generate_compositions.py` Scene 05 | 内嵌 code 块 |

---

## 6. 执行顺序（建议 1 个工作切片）

1. P2-1 节点库 + 03–07 换 mount（画面应与 P1 等价，回归无闪）  
2. P2-2 action-player 接通 03–07  
3. P2-3 两处 camera  
4. P2-5 Scene 05 代码条  
5. P2-4 字幕烧进 PiP  
6. 全链路 `--skip-tts --reuse-presenter` → `pipeline_v2_p2` → scp Mac  
7. （有余力）SFX / mood

每步都可单独渲 `lecture_courseware` 看画面，不必每次跑数字人。

---

## 7. 验收

只看 `outputs/pipeline_v2_p2/final.mp4`：

- [ ] 时长 55–58s，1080×1920  
- [ ] 架构节点不在 Python 里写死坐标  
- [ ] 改 Scene 05 `actions` 能改变粒子/高亮而无需改模板字符串逻辑  
- [ ] ≥1 次 zoom/focus 到 Redis 或单机瓶颈  
- [ ] 底栏字幕可见且不挡数字人  
- [ ] Redis 段有 Cache Aside 代码行高亮  
- [ ] 无 P1 那种拓扑闪烁  

失败回退：字幕可关；Code 可删；节点库不可回退到 PNG。
