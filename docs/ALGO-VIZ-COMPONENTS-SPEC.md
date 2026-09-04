# 通用算法与微观原理可视化组件库规范 (AlgoViz Components Spec)

**版本**：V1.0 Universal Visual Components Specification  
**更新日期**：2026-09-03  
**适用范围**：
- 《LeetCode 经典高频算法精讲》（`leetcode-algorithms`）
- 《系统设计面试通关课》（`system-design`）中后期的微观机制推演（Trie 树、Snowflake 比特位、跳表、布隆过滤器、News Feed Timeline 等）
- 后续新增学科（`python-crash-course`, `ai-agents` 等）

---

## 一、 设计目标与架构原则

### 1. 核心目标
1. **收敛性**：用 **7 种原子级视觉元组件** 覆盖 95% 以上的数据结构与微观原理演示，杜绝为单道题编写专有前端代码。
2. **声明式驱动（DSL-Driven）**：分镜 JSON 仅声明静态数据（如节点列表、指针位置）与动态动作（如移动、摘除、插入），组件负责 SVG 布局与 GSAP 补间动画。
3. **零空图兜底**：任何分镜只要声明了对应组件结构，前端引擎自适应挂载渲染并保证 1080×1920 竖屏排版美观。

---

## 二、 7 大通用组件全景与 DSL 契约

```
                                  AlgoViz 核心组件库
                                         │
    ┌──────────────┬──────────────┬──────┴───────┬──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼              ▼              ▼
1. Array &      2. Linked      3. Hash        4. Tree &      5. Stack &     6. DP Table    7. Rate Limit
   BitLayout       List           Map            Trie           Heap           & Matrix       & Hash Ring
 (双指针/位图)  (单双链表/LRU) (KV桶/冲突链)   (前缀树/二叉树) (单调栈/优先队列) (二维动规网格) (哈希环/令牌桶)
```

---

### 组件 1：一维数组与比特布局 (`array` / `bit_layout`)
* **适用场景**：Two Sum 双指针、二分查找、滑动窗口、Snowflake 64 位切分、BitMap 布局。
* **JSON DSL 契约**：
```json
{
  "array": {
    "items": [
      { "val": 2, "idx": 0, "label": "L" },
      { "val": 7, "idx": 1, "highlight": true },
      { "val": 11, "idx": 2 },
      { "val": 15, "idx": 3, "label": "R" }
    ],
    "pointers": [
      { "name": "left", "target_idx": 0, "color": "#10B981" },
      { "name": "right", "target_idx": 3, "color": "#EF4444" }
    ]
  }
}
```
* **动态动作支持**：
  - `move_pointer`: `{ "type": "move_pointer", "name": "left", "to_idx": 1, "at": 1.2 }`
  - `highlight_item`: `{ "type": "highlight_item", "index": 1, "cls": "active", "at": 1.8 }`

---

### 组件 2：单向/双向链表 (`linked_list`)
* **适用场景**：**LRU Cache**、LFU 缓存、反转链表、朋友圈 News Feed Timeline、跳表层级。
* **JSON DSL 契约**：
```json
{
  "linked_list": {
    "type": "doubly",
    "show_sentinel": true,
    "nodes": [
      { "id": "head", "val": "HEAD", "sentinel": true },
      { "id": "n1", "key": "1", "val": "A", "freq": "最近使用" },
      { "id": "n2", "key": "2", "val": "B" },
      { "id": "n3", "key": "3", "val": "C", "freq": "最久未用" },
      { "id": "tail", "val": "TAIL", "sentinel": true }
    ]
  }
}
```
* **动态动作支持**：
  - `detach_node`: `{ "type": "detach_node", "target": "n2", "at": 0.8 }`（断开前后连线并上浮）
  - `insert_head`: `{ "type": "insert_head", "target": "n2", "after": "head", "at": 1.6 }`（平移至 head 后重新连线）
  - `remove_tail`: `{ "type": "remove_tail", "target": "n3", "at": 2.2 }`（淡出并移除尾节点）

---

### 组件 3：哈希表与键值映射 (`hash_map`)
* **适用场景**：两数之和差值查找、LRU 联动定位、Redis 字典扩容、布隆过滤器哈希槽。
* **JSON DSL 契约**：
```json
{
  "hash_map": {
    "title": "HashMap Key ➔ Node 索引表",
    "entries": [
      { "key": "1", "val_ref": "n1 (Node A)", "status": "active" },
      { "key": "2", "val_ref": "n2 (Node B)", "highlight": true },
      { "key": "3", "val_ref": "n3 (Node C)" }
    ]
  }
}
```
* **动态动作支持**：
  - `map_put`: `{ "type": "map_put", "key": "4", "val": "n4", "at": 1.0 }`
  - `map_highlight`: `{ "type": "map_highlight", "key": "2", "at": 1.5 }`
  - `map_delete`: `{ "type": "map_delete", "key": "3", "at": 2.0 }`

---

### 组件 4：二叉树与前缀树 (`tree` / `trie`)
* **适用场景**：搜索建议 Autocomplete (Trie)、Google Drive 分块差异 (Merkle Tree)、二叉搜索树、LCA。
* **JSON DSL 契约**：
```json
{
  "tree": {
    "type": "trie",
    "root": {
      "val": "ROOT",
      "children": [
        {
          "val": "a",
          "children": [
            { "val": "p", "children": [{ "val": "p", "is_word": true, "word": "app" }] }
          ]
        },
        {
          "val": "b",
          "children": [{ "val": "e", "children": [{ "val": "e", "is_word": true, "word": "bee" }] }]
        }
      ]
    }
  }
}
```
* **动态动作支持**：
  - `traverse_path`: `{ "type": "traverse_path", "path": ["a", "p", "p"], "at": 0.8 }`
  - `pulse_node`: `{ "type": "pulse_node", "target": "app", "at": 2.0 }`

---

### 组件 5：栈与堆/优先队列 (`stack_heap`)
* **适用场景**：单调栈（接雨水/最大矩形）、Top K 搜索热词（小顶堆）、待爬 URL 优先级队列。
* **JSON DSL 契约**：
```json
{
  "stack": {
    "type": "vertical",
    "items": [15, 11, 7, 2],
    "top_pointer": true
  }
}
```
* **动态动作支持**：
  - `push_stack`: `{ "type": "push_stack", "val": 20, "at": 0.8 }`
  - `pop_stack`: `{ "type": "pop_stack", "at": 1.5 }`

---

### 组件 6：动态规划网格与矩阵 (`dp_table`)
* **适用场景**：背包问题、最长公共子序列、二维网格寻路、编辑距离。
* **JSON DSL 契约**：
```json
{
  "dp_table": {
    "rows": ["Ø", "a", "b", "c"],
    "cols": ["Ø", "a", "c"],
    "grid": [
      [0, 0, 0],
      [0, 1, 1],
      [0, 1, 1],
      [0, 1, 2]
    ],
    "active_cell": [3, 2]
  }
}
```
* **动态动作支持**：
  - `fill_cell`: `{ "type": "fill_cell", "row": 3, "col": 2, "val": 2, "from": [[2, 1]], "at": 1.2 }`

---

### 组件 7：限流算法桶与一致性哈希环 (`ring` / `bucket` / `sliding_window`)
* **适用场景**：已在 V4 落地并完善，用于一致性哈希、令牌桶、滑动窗口日志。

---

## 三、 前端渲染与挂载规范 (`scripts/generate_compositions.py`)

在 HTML 模板与 `_wrap` 生成时，统一挂载检测：

```html
<div class="zone-content">
  <div class="svg-canvas-container" id="algo-mount" style="height:620px;"></div>
  <div id="takeaway" class="beat-card active" style="opacity:0;">
    <div style="font-size:26px;line-height:1.5;color:#F8FAFC;">${takeaway}</div>
  </div>
</div>
```

```javascript
// 挂载总入口
if (SCENE.array)       AlgoViz.mountArray("#algo-mount", SCENE.array);
if (SCENE.linked_list) AlgoViz.mountLinkedList("#algo-mount", SCENE.linked_list);
if (SCENE.hash_map)    AlgoViz.mountHashMap("#algo-mount", SCENE.hash_map);
if (SCENE.tree)        AlgoViz.mountTree("#algo-mount", SCENE.tree);
if (SCENE.stack)       AlgoViz.mountStack("#algo-mount", SCENE.stack);
if (SCENE.dp_table)    AlgoViz.mountDpTable("#algo-mount", SCENE.dp_table);
if (SCENE.ring)        AlgoViz.mountRing("#algo-mount", SCENE.ring);
if (SCENE.bucket)      AlgoViz.mountBucket("#algo-mount", SCENE.bucket);
if (SCENE.sliding_window) AlgoViz.mountSlidingWindow("#algo-mount", SCENE.sliding_window);
```

---

## 四、 实施计划与里程碑

1. **Step 1 (规范确立)**：归档 `docs/ALGO-VIZ-COMPONENTS-SPEC.md`，明确所有字段与动作契约。
2. **Step 2 (组件实现)**：在 `assets/scripts/algo-viz.js` 中完整实现 `mountArray`, `mountLinkedList`, `mountHashMap`, `mountTree`, `mountStack`, `mountDpTable`。
3. **Step 3 (动作分发升级)**：在 `assets/scripts/action-player.js` 中接入所有动效指令。
4. **Step 4 (管线与编译器适配)**：升级 `scripts/generate_compositions.py` 与 `scripts/compile_chapter.py`，支持全部 7 大组件。
5. **Step 5 (实战验收)**：升级 LRU Cache 分镜（挂载真实 `linked_list` SVG），运行编译与渲染检验成片。
