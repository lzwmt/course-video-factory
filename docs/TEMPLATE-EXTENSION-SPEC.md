# 系统设计课件模板扩展与技术实现规范 (Template System Specification)

**版本**：V4.0 Architecture Spec  
**更新日期**：2026-09-02  
**状态**：已冻结（Frozen / Ready for Implementation）  
**代码工程**：`/home/lzwmt/project/system-design-hyperframes`

---

## 一、 模板体系架构与自动分发机制

为了支持《System Design Interview》全书 28 章不同场景的技术表达，平台将视频表现形式解耦为三大核心模板矩阵，并由编译器与渲染器实现**根据内容特征全自动路由与分发调用**。

```
                                 章节内容包 / Markdown
                                           │
                                           ▼
                            ┌─────────────────────────────┐
                            │  scripts/compile_chapter.py │
                            │   (静态强校验 & 模板自适应嗅探) │
                            └──────────────┬──────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│   Template A     │             │   Template B     │             │   Template C     │
│ system_evolution │             │    estimation    │             │    algorithm     │
├──────────────────┤             ├──────────────────┤             ├──────────────────┤
│ 架构拓扑演进型   │             │ 封底估算推演型   │             │ 算法机制交互型   │
│ • 节点/边/连线   │             │ • 算式/步进黑板  │             │ • 哈希环/令牌桶  │
│ • 数据包流转     │             │ • 单位阶梯换算   │             │ • 滑动窗口网格   │
│ • `arch-graph.js`│             │ • `calc-board.js`│             │ • `algo-viz.js`  │
└────────┬─────────┘             └────────┬─────────┘             └────────┬─────────┘
         │                                │                                │
         └────────────────────────────────┼────────────────────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │ scripts/generate_compositions.py│
                         │   (分镜 HTML 工厂 & GSAP 动效)   │
                         └────────────────┬────────────────┘
                                          ▼
                         ┌─────────────────────────────────┐
                         │   scripts/produce_pipeline.py   │
                         │ (HyperFrames + Presenter Studio)│
                         └────────────────┬────────────────┘
                                          ▼
                                1080×1920 竖屏交付成片
```

### 1. 自动调用与路由工作原理

| 路由层级 | 触发机制 | 自动化处理逻辑 |
| :--- | :--- | :--- |
| **一级路由（章节级）** | `chapter.json` / `catalog.json` 声明或特征嗅探 | 编译器读取 `"template"` 字段（未指定时通过关键词/字段特征自动推断），自动载入对应的 `templates/<template_name>.json` 执行约束与配方检查。 |
| **二级路由（分镜级）** | `scenes.json` 中的 `"scene_type"` | 页面生成器根据分镜类型（如 `hook`、`calc_step`、`hash_ring`、`summary`）自动匹配对应的 Composition 工厂函数，并挂载对应的前端 JS 动画组件。 |

---

## 二、 模板 A：系统拓扑演进型 (`templates/system_evolution.json`)

* **适用章节**：Chapter 01 (Scaling), 08 (URL Shortener), 11 (News Feed), 13 (Search Autocomplete) 等。
* **教学叙事节奏**：`Hook (量级冲击) ➔ Problem (瓶颈爆发) ➔ Evolve* (单点拆分与组件演进) ➔ Flow (全链路数据流) ➔ Summary (核心三原则)`
* **前端视觉载体**：`assets/scripts/arch-graph.js`（SVG 拓扑容器） + `action-player.js`。

### 核心 DSL 动作
* `add_node` / `node`：按拓扑网格入场节点（`web`, `redis`, `mysql`, `mq`, `worker`, `lb` 等）。
* `connect`：生成带光效的 SVG 连接线条。
* `packet`：发射红/绿/蓝/橙颜色数据包粒子，模拟读命中、回源、写入与异步任务。
* `zoom` / `focus`：镜头平滑聚焦局部组件，弱化其余节点。

---

## 三、 模板 B：封底估算推演型 (`templates/estimation.json`)

* **适用章节**：Chapter 02 (Back-of-the-envelope Estimation) 及各章节的前置容量规划。
* **教学叙事节奏**：`Hook (业务量级提出) ➔ Assumptions (基准假设卡) ➔ Calc_Step* (QPS/存储/带宽分步推导) ➔ Rules (2的幂次方/时间换算经验法) ➔ Summary (指标收束表)`
* **前端视觉载体**：`assets/scripts/calc-board.js`（深色科技感动态计算黑板）。

### 1. 数据契约与分镜扩展 (`scenes.json`)

```json
{
  "scene": "03",
  "id": "03_calc_qps",
  "scene_type": "calc_step",
  "title": "估算平均读写 QPS",
  "badge": "步骤 1 · QPS 估算",
  "narration": "5亿日活、每人每天读2次。一天8.6万秒近似10万秒，算下来平均读 QPS 约 1.15 万。",
  "keywords": ["500M DAU", "86,400s", "11.5k QPS"],
  "calc_board": {
    "title": "Read QPS Calculation",
    "formula": "QPS = \\frac{500,000,000 \\times 2}{86,400 \\text{ s}}",
    "steps": [
      { "label": "日总请求数", "expr": "500M × 2 = 10 亿次/天" },
      { "label": "时间近似换算", "expr": "1 天 ≈ 100,000 秒 (简化面试心算)" },
      { "label": "平均读 QPS", "expr": "10^9 ÷ 10^5 = 10,000 req/s", "highlight": true }
    ],
    "result": {
      "metric": "Avg Read QPS",
      "value": 11574,
      "approx": "~10k - 12k",
      "unit": "req/s"
    }
  },
  "actions": [
    { "type": "calc_show_step", "index": 1, "at": 0.8 },
    { "type": "calc_show_step", "index": 2, "at": 2.2 },
    { "type": "calc_roll_result", "target": "#metric-qps", "from": 0, "to": 11574, "at": 3.5, "sfx": "success" }
  ]
}
```

### 2. 前端组件实现 (`assets/scripts/calc-board.js`)
* **动态公式渲染**：内嵌深色网格卡片，公式高亮着色，支持分步淡入并伴随代入下划线。
* **数字翻滚动画**：集成 GSAP 计数器，自动格式化千分位（`11,574`）及常用缩写（`11.5K`、`1.2 TB/day`）。
* **单位梯度阶梯图 (`units_ladder`)**：动态绘制 $2^{10} = 1KB \to 2^{20} = 1MB \to 2^{30} = 1GB \to 2^{40} = 1TB$ 知识阶梯卡片。

---

## 四、 模板 C：算法机制交互型 (`templates/algorithm.json`)

* **适用章节**：Chapter 04 (Rate Limiter), 05 (Consistent Hashing), 06 (KV Store), 07 (Unique ID Generator)。
* **教学叙事节奏**：`Hook (并发/数据倾斜痛点) ➔ Naive (朴素算法失效) ➔ Algo_Viz* (算法核心机制动态演示) ➔ Edge_Case (宕机/溢出极限处理) ➔ Summary (选型总结)`
* **前端视觉载体**：`assets/scripts/algo-viz.js`（算法动态图形引擎）。

### 1. 一致性哈希环 (`hash_ring`)
* **视觉要素**：SVG 渐变圆环、物理节点标识（Node 1/2/3）、虚拟节点光斑分布、Key 落点顺时针路由飞线。
* **动作支持**：
  * `ring_init`：挂载圆环与初始节点。
  * `ring_route`：高亮落点 Key 并沿顺时针扫描直到找到第一台机器。
  * `ring_node_down`：标记某节点红色下线，动态重路由受影响 Key 到下一可用节点。

```json
{
  "type": "ring_route",
  "key": "user_id_9527",
  "angle": 135,
  "target_node": "Node_2",
  "at": 1.6,
  "sfx": "success"
}
```

### 2. 限流器令牌桶与漏桶 (`token_bucket` / `sliding_window`)
* **视觉要素**：容器容量边框、动态注水/注令牌粒子流、请求到达时令牌扣减与红波溢出拦截。
* **动作支持**：
  * `bucket_refill`：恒定速率填充令牌（绿光粒子滴入）。
  * `bucket_consume`：请求消耗令牌（扣减动画并放行蓝光数据包）。
  * `bucket_reject`：无可用令牌，请求变红并震动驳回（`sfx: error`）。

---

## 五、 后端编译器与自动推断机制 (`scripts/compile_chapter.py`)

### 1. 静态合法性校验升级
```python
def validate_template_recipe(entry: dict, chapter_data: dict, scenes: list[dict], template: dict) -> list[str]:
    """根据模板类型执行强类型规则校验。"""
    errors = []
    template_type = template.get("type", "system_evolution")
    
    if template_type == "estimation":
        for s in scenes:
            if s.get("scene_type") == "calc_step" and not s.get("calc_board"):
                errors.append(f"Scene {s.get('scene')}: calc_step 分镜缺少 'calc_board' 结构定义")
    elif template_type == "algorithm":
        for s in scenes:
            if s.get("scene_type") == "hash_ring" and not s.get("ring"):
                errors.append(f"Scene {s.get('scene')}: hash_ring 分镜缺少 'ring' 节点定义")
    return errors
```

### 2. 自适应模板嗅探器 (Heuristic Sniffer)
当外部 Markdown 或未标记章节输入时，编译器自动判定模板类型：
1. 若分镜包含 `calc_board`、`formula`、`steps` ➔ 自动识别为 **`estimation`**。
2. 若分镜包含 `hash_ring`、`token_bucket`、`sliding_window` ➔ 自动识别为 **`algorithm`**。
3. 若分镜包含 `nodes`、`edges` ➔ 自动识别为 **`system_evolution`**。

---

## 六、 渲染管线与 QA 质量门禁兼容性

所有新增模板生成的分镜 HTML 必须统一接入既有的 QA 门禁（`scripts/qa_render.py`）：
1. **统一视口与帧率**：严格输出 1080×1920 竖屏 @ 30fps。
2. **GSAP 动效绑定**：必须向 `window.__timelines["shot_<id>"]` 暴露暂停状态的 GSAP timeline，由 HyperFrames 无头渲染器逐帧驱动。
3. **数字人画中画**：通用支持 `host`（280px）、`support`（180px）、`pip`（140px）、`hidden`（隐藏）四种自适应档位。
4. **音频时长窗口**：单镜头时长与 TTS 音频完全对齐，总成片时长偏差严格控制在 $\pm 8\text{s}$ 质检门禁内。

---

## 七、 实施与集成路线图

1. **Step 1（估算模板与组件落地）**：编写 `calc-board.js` 与 `templates/estimation.json`，在 `generate_compositions.py` 中接入 `generate_calc_composition()`。
2. **Step 2（Chapter 02 封底估算实战出片）**：录入 `content/chapters/02-estimation/` 数据，全链路编译渲染出片并通过 QA 门禁。
3. **Step 3（算法模板与动效引擎落地）**：编写 `algo-viz.js` 与 `templates/algorithm.json`。
4. **Step 4（Chapter 04 限流器 / 05 一致性哈希实战出片）**：录入算法章节并验证复杂交互动效。
