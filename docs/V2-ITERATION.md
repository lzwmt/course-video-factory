# 系统设计课件视频 · V2 迭代文档

**日期**：2026-03-27（P1 更新：2026-09-01）  
**工程**：`/home/lzwmt/project/system-design-hyperframes`  
**数字人**：`/home/lzwmt/project/ai-presenter-studio`  
**V1 样片**：`outputs/pipeline/final.mp4`（Shot 01–03 课件页）  
**V2 P1 成片**：`outputs/pipeline_v2_p1/final.mp4`（8 Scene，56.6s，1080×1920）  
**Mac 同步**：`~/Downloads/final_v2_p1.mp4`

本文确认 V2 批评哪些成立、哪些被夸大，并给出按 ROI 排序的落地计划。  
**原则：先改 60 秒样片的导演和画面，再抽引擎，最后才做自动导演。不要一次改全部。**

---

## 0. 一句话结论

当前管线是 **课件页生成器**，不是 **技术短视频导演器**。

```text
V1：数字人（固定右下角圆） + PPT 卡片 + 白色架构 PNG

V2：讲解逻辑
        ├─ 数字人   → 说什么
        ├─ 动画     → 怎么动
        ├─ 架构图   → 建立空间关系
        ├─ 代码     → 证明
        └─ 字幕     → 抓重点
```

短视频表现层的问题几乎全部成立，且被成片帧证实。被夸大的是「必须先拆成 8 模块 `/video-engine`」——渲染器已经在，缺的是 Scene / Motion / Camera。

---

## 1. 现状（V1）

### 1.1 生产链路

```text
data/*-shots.json
  → scripts/build_timed_shots.py     TTS + beat 测时
  → scripts/generate_compositions.py cover / list / diagram
  → HyperFrames Chrome 渲染
  → ffmpeg concat → lecture_courseware.mp4
  → ai-presenter-studio/pipeline.py  数字人
  → composer.py --layout pip --avatar-size 280 → final.mp4
```

### 1.2 镜头合同

- 原子单位是 `shot` = 一页 PPT（`slide: 001…017`）
- 三种模板：`cover` / `list` / `diagram`
- `diagram` 把 `assets/images/*.png` 放进 `.diagram-card`
- 动画只有 GSAP `opacity` + 轻微 `y` / `scale`
- 数字人全程右下角 280px 圆形 PiP（280/1920 ≈ 14.6% 高度）

### 1.3 样片时间轴（`data/shots_timed.json`）

| 时间 | Shot | 内容 | 时长 |
|---|---|---|---|
| 0–16.8s | 01 封面 | 徽章 + 大标题 + 演进路径卡 | 16.8s |
| 16.8–47.8s | 02 这一章在讲什么 | 4 张要点卡 + 举例框 | 31.1s |
| 47.8–57.8s | 03 单机部署 | 白底架构 PNG 整图淡入 | 10.0s |

Shot 02 占全片约 **54%**。结构就是：封面 → 这一章讲什么 → 单机图。

### 1.4 画面分区（现状）

```text
1080 × 1920
┌────────────────────┐
│                    │  上半空
│   标题 / 徽章       │
│                    │
│   内容卡片          │  往中间塞
│                    │
│                    │  下半空
│                 👨  │  固定 280px 圆
└────────────────────┘
```

封面使用 `justify-content: center`。  
`.composition-root` padding 为 `100px 72px 160px 72px`。  
没有 80 / 150 / 1250 / 350 三区。  
`.pip-safety-guide` 为 `display: none`，HTML 并不真的给数字人留底栏。

---

## 2. 问题对照

| # | 批评点 | 判定 | 证据 |
|---|---|---|---|
| 1 | 数字人 + PPT 卡 + 架构图三件套 | **存在** | 仅 cover / list / diagram |
| 2 | 竖屏上半空、下半空 | **存在** | 封面垂直居中；底 padding 160px |
| 3 | 数字人固定右下角 ~15% | **存在** | `--avatar-size 280`；280/1920 ≈ 14.6% |
| 4 | 以 PPT 页而不是 Scene 为单位 | **存在** | `slide: 001…017` |
| 5 | 开头是传统封面 | **存在** | Shot 01 章节徽章 + 课程标题 |
| 6 | 「这一章在讲什么」过长 | **存在** | Shot 02 = 31.1s |
| 7 | 架构图是白底图片卡 | **存在** | `assets/images/*.png` + `.diagram-card` |
| 8 | 图一次出现后停住 | **存在** | `opacity + scale 0.98→1`，1.5s 出 takeaway |
| 9 | 缺矛盾 / 过载 / 瓶颈戏 | **存在** | 无 CPU 条、用户暴增、OVERLOAD |
| 10 | 扩容组件一次铺开 | **存在** | 每节一张完整 PNG |
| 11 | 无请求粒子 / SVG 节点图 | **存在** | 无 `connect` / `packet` |
| 12 | 无 MotionEngine / Scene JSON | **存在** | 生成器直接写 `gsap.to` |
| 13 | 无代码 / 终端 / 真实浏览器 | **存在** | 无对应模板 |
| 14 | 字幕系统 | **更差** | 连底栏字幕都没有；TTS 无词时间戳 |
| 15 | 数字人无情绪 / 无三档 | **存在** | `--style auto` + 固定 PiP |
| 16 | 无 Zoom / Pan / Focus | **存在** | 无 camera |
| 17 | 转场硬切 / 淡入 | **存在** | ffmpeg `-c copy` |
| 18 | 无克制 SFX / BGM 分层 | **存在** | 只有 TTS + 数字人声 |
| 19 | 结尾无 CTA | **存在** | Shot 17 是五条原则列表 |
| 20 | 每秒信息量偏低 | **存在** | Cover 16.8s 几乎静止；卡 4–12s 一张 |

「这一章在讲什么」不是多页重复，而是封面口播与 Shot 02 **语义重复**，再加 Shot 02 占半条片。

---

## 3. 不要推倒重来的部分

### 3.1 必须保留

- 1080×1920 锁定
- 暗色科技风、CSS 变量、主色已接近 `#3B82F6`
- 字体：Inter + Noto Sans SC + JetBrains Mono
- 本地 GSAP、HyperFrames Chrome 渲染、ffmpeg 拼接
- beat 级 TTS 测时（Edge / Qwen）
- 数字人管线（LivePortrait / Wav2Lip / GFPGAN）

### 3.2 批评过重

- 「固定 15%」指高度占比。280px **宽度**已落在主持档（250–300）。问题是永远同一位置、圆形摆件、不让位给架构图，不是单纯太小。
- 「底部白字幕要重做」——当前没有字幕轨道。beat 卡片在承担字幕职责。
- 「8 模块 `/video-engine`」是目标架构，不是当前 blocker。
- 真实浏览器 DevTools、词级时间戳、LLM 自动导演属于 P3，不进第一轮。

### 3.3 额外工程债（批评未点名，但会卡住 V2）

1. 封面标题回退成「封面」：`shots_timed.json` 的 `title` 被生成器当主标题。
2. diagram takeaway 写死「架构关键：整图完整可见」——制作备注，不是教学内容。
3. `ch1-full-shots.json` 从 Shot 04 起无 `duration_sec`，GSAP 全挤在 `t=0`。
4. `pip-safety-guide` 不占位，底栏布局与 PiP 未对齐。

---

## 4. V2 画面规范

### 4.1 三区布局（第一优先级）

```text
1080 × 1920
┌────────────────────┐
│  章节标签            │  80   现在讲什么
│  主标题              │  150
├────────────────────┤
│                    │
│     核心内容区       │  1250 把知识讲明白
│                    │
├────────────────────┤
│  数字人 / 字幕       │  350  说 + 抓重点
└────────────────────┘
```

- 顶部：章节标签 + 一句 Hook 标题。标题信息可以小。
- 中间：知识可视化。禁止再往中间堆 5 张长文卡片。
- 底部：数字人 + 双层字幕。HTML 必须真的留出 350px，不能靠 `display: none` 的安全区。
- 封面禁止 `justify-content: center`。

### 4.2 数字人三档（不要只放大）

| 状态 | 宽度 | 位置 | 使用 |
|---|---|---|---|
| A 主持 | 250–300px | 中下 / 偏中 | 开场、总结 |
| B 陪讲 | 160–220px | 右下 | 架构图、代码 |
| C 旁白 | 100–150px | 左下 | 大型架构动画、粒子流 |

Scene 合同带 `avatar: { state, x, y, size }`。  
`produce_pipeline.py` 按 scene 调 composer，禁止全局写死 `--avatar-size 280`。

情绪最小集（P2 再做）：`normal / explain / thinking / warning / conclusion`。

### 4.3 镜头语言

只允许三种镜头运动：

1. **Zoom** — 强调重点  
2. **Pan** — 跟随数据流  
3. **Focus** — 突出当前组件  

转场禁止淡入淡出 / 翻页 / 旋转。优先：

- 线条延伸到下一场景
- 节点扩大成为下一镜头（连续空间转场）

### 4.4 信息密度

同一 Scene 内变化，不是每秒切镜。

| 时段 | 变化间隔 |
|---|---|
| 0–3s Hook | 0.3–0.7s |
| 3–15s | 1–2s |
| 15–45s | 1.5–3s |
| 45–60s | 1–2s |

### 4.5 视觉与声音 token

```css
--color-primary:   #3B82F6;
--color-success:   #22C55E;
--color-warning:   #F59E0B;
--color-danger:    #EF4444;
--color-text:      #F8FAFC;
--color-secondary: #94A3B8;
```

禁止组件内硬编码色值。

字体：中文 Noto Sans SC / 思源黑体；英文 Inter；代码 JetBrains Mono；数字 Inter。

音效只 5 类，克制使用：`click / pop / whoosh / success / error`。  
人声 100%；BGM 5–10%（P1 可先不加）；SFX 10–20%。

### 4.6 架构图

停用白底 PNG 作为主视觉。改为深色背景 + 原生 SVG/HTML 节点。

PNG 可留作参考，不再进入主画面。

---

## 5. 60 秒样片结构（第一章 V2）

文案方向仍是「从单机按瓶颈演进」，但第一帧必须是问题，不是《系统设计第一章》。

| 时间 | Scene | 画面 | 数字人 |
|---|---|---|---|
| 0–3s | Hook | 近景提问 + 100→1,000→10,000→100,000 + SERVER ERROR | A 主持 |
| 3–7s | Problem | USER → WEB → DATABASE；用户涌入；CPU 35→65→89→100；OVERLOAD | A→B |
| 7–12s | Single Server | User / Web / DB 逐个出现（0.0 / +0.4 / +0.4）再发包 | B 陪讲 |
| 12–17s | Bottleneck | 100 users OK → 10,000；CPU/RAM/DB 告警；❌ 数据库成为瓶颈 | B · Warning |
| 17–23s | Scale Web | 单机 → Web × 2 | B |
| 23–28s | Load Balance | LB 出现 | B |
| 28–34s | Cache | Redis 出现（数据库慢 → Redis → 减少 DB 请求） | B |
| 34–40s | MQ | MQ 出现 | B |
| 40–47s | Full Architecture | 完整架构 | C 旁白 |
| 47–53s | Request Flow | 请求粒子；Redis HIT 绿 / MISS 红 → MySQL | C，可左下 |
| 53–57s | Summary + CTA | 三条结论 + 「下一集，我们拆开 Redis。」 | A 主持 |

必须砍掉：

- 传统封面当第一帧
- 「这一章在讲什么」作为独立长镜头
- 「请看这张图」课件口播
- diagram 里「整图完整可见」
- 结尾突然结束

扩容组件禁止一次全部放出。每出现一个组件，必须给「为什么增加它」。

---

## 5.1 当前进度（2026-09-01）

| 阶段 | 状态 | 证据 |
|---|---|---|
| P0 内容合同 | **完成** | `data/ch1-v2-scenes.json` 8 Scene；口播约 218 词；Edge-TTS `zh-CN-YunxiNeural`；`outputs/pipeline_v2_p0/final.mp4` 56.3s |
| P1 画面系统 | **基本完成** | 三区 CSS、MotionEngine、原生 SVG 拓扑、Scene 级三档 PiP；`outputs/pipeline_v2_p1/final.mp4` 56.6s |
| P1 闪烁修复 | **完成** | 去掉 `.node-box { transition: all }`；SVG 透明度改 `attr`；关闭 GSAP `force3D` |
| P2 五大技术镜头 | **未开始** | 见第 6 节 P2 任务清单 |
| P3 自动导演 | **不做** | Scene 运行时未稳定前禁止 LLM 拆镜 |

P1 已落地文件：

- `assets/styles/global.css` — 三区 padding `80 / 72 / 350` + color token
- `assets/scripts/motion.js` — enter / connect / packet / highlight / zoom / pulse / shake / counter
- `scripts/generate_compositions.py` — hook / problem / evolve / flow / summary + SVG 节点
- `scripts/produce_pipeline.py` — 按 Scene 切数字人：host 280 中下 / side 180 右下 / pip 140 左下

P1 已知缺口（不挡验收，进 P2）：

1. `zoom` / `pan` / `focus` API 已有，样片里几乎没用（粒子与入场为主）。
2. `ai-presenter-studio/composer.py` 未加 `avatar-position`（仓库外）；三档合成在本仓 ffmpeg 完成。
3. 底栏 350px 已留白，**字幕轨道仍未挂**。
4. 无 SFX / BGM；无代码 / 终端 / 浏览器镜头。
5. 节点库仍内联在生成器，未抽 `compositions/components/arch-graph`。

---

## 6. 分阶段计划

### P0 · 内容合同（1–2 天） · **已完成**

**目标**：把「一页 PPT」改成「一个 Scene 一个动作」。

动作：

- 新增 `data/ch1-v2-scenes.json`（旧 `ch1-shots.json` 只读保留）
- 按第 5 节写旁白、时长、avatar 状态、画面动作
- 先用现有生成器出一版**文案/时长**对的样片，画面可以仍旧

完成定义：60s 口播不再是「封面 + 本章概览 + 请看这张图」。

### P1 · 画面系统 · **已完成（缺口见 5.1）**

对应最高 ROI 的 5 件事。**不要先搬家到 `/video-engine`。**

1. **三区布局** — 写入 `assets/styles/global.css`
2. **数字人三档** — 改 `produce_pipeline.py` + composer 参数
3. **架构图 HTML/SVG 化** — P1 只做 `single-server`：`user / web / db` + `connect()`
4. **请求粒子** — 蓝点 = HTTP Request；HIT 绿 / MISS 红
5. **Camera zoom / pan / focus** — 薄封装，禁止为动而动

MotionEngine 先做现有 GSAP 的薄 API：

```js
motion.enter()
motion.exit()
motion.focus()
motion.highlight()
motion.zoom()
motion.pan()
motion.connect()
motion.packet()
motion.pulse()
motion.shake()
motion.type()
```

调用形态：

```js
await motion.enter("user");
await motion.connect("user", "nginx");
await motion.packet("user", "nginx");
await motion.highlight("nginx");
```

最终希望：`scene.play("single-server")`，而不是每个镜头手写 `gsap.timeline`。

P1 代码切入顺序：

1. `assets/styles/global.css` — 三区 layout + color token
2. `data/ch1-v2-scenes.json` — Scene 合同
3. `scripts/generate_compositions.py` — 新增 `hook` / `graph` / `summary`；list 不再当主镜头
4. `assets/scripts/motion.js` — GSAP 封装
5. `compositions/components/arch-graph.html` — SVG 节点 + packet
6. `scripts/produce_pipeline.py` — 按 scene 传 avatar size/position
7. 底栏先空出 350px；字幕轨道 P2 再挂

P1 完成定义：`outputs/pipeline/final_v2.mp4` 不再像课件录屏。

### P2 · 五大技术镜头 + 可复用导演运行时  ← **下一阶段**

在 P1 样片跑通之后再加。原则：只在「证明」需要时使用，不为炫技加镜。

#### P2 目标

同一条 60s 片里：可复用架构图组件 + 至少一种证明镜头（代码或终端）+ 底栏关键词字幕 + 至少一次有意义的 zoom/focus。

#### P2 任务清单（按顺序）

| # | 任务 | 切入点 | 完成定义 |
|---|---|---|---|
| P2-1 | **抽出架构图节点库** | `compositions/components/arch-graph.js`（或 SVG sprite） | Client / LB / Web / Redis / MySQL / MQ / Worker 可按 Scene 声明拼图，不再在 `generate_compositions.py` 里硬编码坐标 |
| P2-2 | **声明式 Scene 动作** | `data/ch1-v2-scenes.json` 的 `actions[]` 真正驱动 GSAP | 生成器读 `packet` / `connect` / `highlight` / `metric`，少写手搓 timeline |
| P2-3 | **Camera 真正用上** | `motion.zoom` / `focus` 挂到 Bottleneck / Cache / Full Flow | 至少 1 次 zoom 到 Redis 或 DB 瓶颈节点；禁止空转镜头 |
| P2-4 | **底栏关键词字幕** | `produce_pipeline.py` + SRT/ASS | 双层：口播句 + 关键词（Nginx / Redis / MQ）；避开数字人圆形 |
| P2-5 | **Code Scene 模板** | `generate_code_composition` | 6–10 行；当前行放大，其余降透明度；第一章可选「Cache Aside 伪代码」插在 Scene 05 后 2–3s（总时长仍压在 55–58s） |
| P2-6 | **Terminal Scene 模板** | `generate_terminal_composition` | 逐字 `curl` 或延迟对比；与口播对齐，不做空转打字机 |
| P2-7 | **数字人情绪最小集** | 旁白语义 → `normal / explain / thinking / warning / conclusion` | 先做字幕色/边框/节点告警联动；LivePortrait style 有接口再接 |
| P2-8 | **克制 SFX** | ffmpeg 混音，仅 5 类 | 粒子到达 / OVERLOAD / 缓存 HIT 各最多 1 次；人声 100%，SFX 10–20%，BGM 仍可不加 |
| P2-9 | **composer 位置参数（可选）** | 若可改 `ai-presenter-studio/composer.py` | `--avatar-position bottom_left\|center_bottom\|bottom_right`；否则继续本仓 ffmpeg |

P2 **明确后置**（不要挤进本轮）：

- Browser Scene / CDP Network 面板（P2-extra，证明缓存命中时再开）
- 词级时间戳（Edge 没有稳定 word timestamps 时用句级 + 关键词高亮即可）
- LLM 自动导演（P3）
- `/video-engine` 搬家

P2 建议验收片：`outputs/pipeline_v2_p2/final.mp4`，同步 Mac `~/Downloads/final_v2_p2.mp4`。

### P3 · 壁垒层（最后做）

```text
主题 → LLM → 技术脚本 → Scene Planner
                ├─ TTS + 词时间戳 → 数字人
                └─ Scene JSON → MotionEngine → HTML/GSAP
                            ↓
                      Headless Chrome → Frames → FFmpeg → 1080×1920
```

Scene JSON 示例：

```json
{
  "scene": "single_server",
  "duration": 8,
  "voice": "单机架构很简单...",
  "avatar": { "state": "B", "size": 180 },
  "elements": [
    { "type": "node", "id": "user" },
    { "type": "node", "id": "server" },
    { "type": "node", "id": "mysql" }
  ],
  "animations": [
    { "type": "connect", "from": "user", "to": "server" },
    { "type": "packet", "from": "user", "to": "server" }
  ]
}
```

目标输入：

```json
{
  "title": "为什么单机扛不住百万用户？",
  "duration": 60,
  "style": "dark-tech",
  "avatar": "male-tech-01"
}
```

自动拆 01 Hook … 06 Summary。  
**P3 之前不要做 LLM 自动导演。** 现在缺的是人工导演过的 Scene 运行时。

目录形态到 P3 再收：

```text
/video-engine
├── core/{scene,timeline,camera,motion}
├── components/{title,card,code,terminal,browser,architecture,node,subtitle}
├── avatar/{liveportrait,wav2lip,gfpgan}
├── voice/{edge-tts,qwen3-tts}
├── renderer/{chrome,cdp,ffmpeg}
└── scenes/{hook,architecture,code,terminal,browser,summary}
```

---

## 7. 明确不在当前范围

- 把 17 个 Shot 全量重渲成「更精美的 PPT」
- 把数字人一律放大
- 继续往 `list` 模板塞卡
- 为 CDN / MQ / 分片各做一套完整自动导演
- 先重构 8 模块 monorepo
- 上复杂 BGM 和传统 PPT 转场包

---

## 8. 验收

只看一条样片：`outputs/pipeline/final_v2.mp4`。

P0 过线：口播结构符合第 5 节，无「这一章在讲什么」长镜头。  
P1 过线：三区布局 + 数字人会换档 + 单机图是 SVG 节点（不是白底 PNG）+ 至少一次粒子请求 + 至少一次 zoom/focus。  
P2 过线：同一条片里出现代码或终端镜头，底栏有关键词字幕。  
P3 过线：同一 Scene JSON 可重放，不必手写 `gsap.to`。
