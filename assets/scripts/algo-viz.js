/**
 * AlgoViz - Dynamic Algorithm Visualization Engine (Consistent Hashing, Rate Limiting, Sliding Window)
 */
(function (global) {
  const DEG2RAD = Math.PI / 180;

  function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
    const rad = (angleInDegrees - 90) * DEG2RAD;
    return {
      x: centerX + radius * Math.cos(rad),
      y: centerY + radius * Math.sin(rad)
    };
  }

  function describeArc(x, y, radius, startAngle, endAngle) {
    const start = polarToCartesian(x, y, radius, endAngle);
    const end = polarToCartesian(x, y, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    return ["M", start.x, start.y, "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y].join(" ");
  }

  // --- 1. Consistent Hash Ring Visualizer ---
  function mountRing(containerSelector, ringData) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;

    const cx = 468;
    const cy = 280;
    const r = 210;

    const defaultNodes = [
      { id: "node_1", name: "Node 1", angle: 30, color: "#3B82F6", ip: "192.168.1.10" },
      { id: "node_2", name: "Node 2", angle: 150, color: "#10B981", ip: "192.168.1.11" },
      { id: "node_3", name: "Node 3", angle: 270, color: "#F59E0B", ip: "192.168.1.12" }
    ];

    const nodes = (ringData && ringData.nodes) || defaultNodes;
    const vnodes = (ringData && ringData.vnodes) || [];

    const nodeElements = nodes
      .map((n) => {
        const p = polarToCartesian(cx, cy, r, n.angle);
        return `
        <g id="ring-${n.id}" class="ring-node-group" opacity="0">
          <circle cx="${p.x}" cy="${p.y}" r="32" fill="#0F172A" stroke="${n.color || '#3B82F6'}" stroke-width="3" class="ring-node-circle"/>
          <text x="${p.x}" y="${p.y - 42}" text-anchor="middle" fill="#F8FAFC" font-size="18" font-weight="700">${n.name}</text>
          <text x="${p.x}" y="${p.y + 6}" text-anchor="middle" fill="${n.color || '#3B82F6'}" font-size="14" font-weight="700">${n.angle}°</text>
          ${n.ip ? `<text x="${p.x}" y="${p.y + 48}" text-anchor="middle" fill="#64748B" font-size="12">${n.ip}</text>` : ""}
        </g>`;
      })
      .join("");

    const vnodeElements = vnodes
      .map((vn, idx) => {
        const p = polarToCartesian(cx, cy, r, vn.angle);
        return `
        <g id="vnode-${idx}" class="ring-vnode-group" opacity="0">
          <circle cx="${p.x}" cy="${p.y}" r="8" fill="${vn.color || '#60A5FA'}" opacity="0.85"/>
          <text x="${p.x}" y="${p.y + 18}" text-anchor="middle" fill="#94A3B8" font-size="10">${vn.label || ''}</text>
        </g>`;
      })
      .join("");

    el.innerHTML = `
      <svg class="svg-canvas" viewBox="0 0 936 560" id="ring-svg">
        <defs>
          <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#3B82F6" stop-opacity="0.8"/>
            <stop offset="50%" stop-color="#8B5CF6" stop-opacity="0.8"/>
            <stop offset="100%" stop-color="#EC4899" stop-opacity="0.8"/>
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>
        <!-- Background Track Ring -->
        <circle id="ring-track" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#1E293B" stroke-width="8" stroke-dasharray="6 6"/>
        <circle id="ring-glow-track" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="url(#ringGrad)" stroke-width="4" opacity="0"/>
        
        <!-- Directional indicator -->
        <text x="${cx}" y="${cy - 30}" text-anchor="middle" fill="#64748B" font-size="16" font-family="JetBrains Mono">Consistent Hash Ring [0, 2^32 - 1]</text>
        <text x="${cx}" y="${cy}" text-anchor="middle" fill="#3B82F6" font-size="28" font-weight="700">↻ 顺时针路由</text>
        <text x="${cx}" y="${cy + 28}" text-anchor="middle" fill="#94A3B8" font-size="14">Clockwise Lookup</text>

        <!-- Dynamic Scan Beam / Route Arc -->
        <path id="ring-scan-arc" d="" fill="none" stroke="#60A5FA" stroke-width="6" stroke-linecap="round" opacity="0" filter="url(#glow)"/>

        <!-- Virtual Nodes -->
        ${vnodeElements}

        <!-- Physical Nodes -->
        ${nodeElements}

        <!-- Key Spot Marker & Fly line -->
        <g id="ring-key-spot" opacity="0">
          <circle id="ring-key-circle" cx="${cx}" cy="${cy}" r="12" fill="#EF4444" filter="url(#glow)"/>
          <text id="ring-key-text" x="${cx}" y="${cy - 20}" text-anchor="middle" fill="#FCA5A5" font-size="16" font-weight="700">Key</text>
        </g>
        <line id="ring-route-line" x1="${cx}" y1="${cy}" x2="${cx}" y2="${cy}" stroke="#22C55E" stroke-width="4" stroke-dasharray="6 4" opacity="0"/>
      </svg>
    `;
  }

  // --- 2. Token Bucket / Rate Limiter Visualizer ---
  function mountBucket(containerSelector, bucketData) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;

    const capacity = (bucketData && bucketData.capacity) || 10;
    const refillRate = (bucketData && bucketData.refillRate) || "5 tokens/sec";

    el.innerHTML = `
      <div class="bucket-viz-container">
        <div class="window-header">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">Token Bucket Limiter · 令牌桶算法</div>
          <div class="window-badge">RATE LIMITER</div>
        </div>
        <div class="bucket-viz-body">
          <div class="bucket-left-col">
            <div class="bucket-refill-emitter">
              <div class="emitter-label">恒定注水/令牌流 (${refillRate})</div>
              <div id="bucket-emitter-pipe" class="emitter-pipe">
                <div id="token-drop-particle" class="token-particle" style="opacity:0;"></div>
              </div>
            </div>
            <div id="bucket-vessel" class="bucket-vessel">
              <div id="bucket-water" class="bucket-water" style="height: 60%;"></div>
              <div class="bucket-capacity-label">Max: ${capacity} Tokens</div>
              <div id="token-count-box" class="token-count-display">
                <span id="token-count-val">6</span> / ${capacity}
              </div>
            </div>
          </div>
          <div class="bucket-right-col">
            <div class="bucket-request-flow">
              <div class="flow-title">客户端请求流入 (Incoming Requests)</div>
              <div class="request-queue-track">
                <div id="req-pkt-1" class="req-packet" style="opacity:0;">Req #1</div>
                <div id="req-pkt-2" class="req-packet" style="opacity:0;">Req #2</div>
                <div id="req-pkt-3" class="req-packet reject" style="opacity:0;">Req #3 (溢出)</div>
              </div>
              <div id="gate-decision-box" class="gate-decision-box" style="opacity:0;">
                <span id="gate-status-text" class="status-allow">PASS: 扣减 1 令牌并放行</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // --- 3. Sliding Window Log Visualizer ---
  function mountSlidingWindow(containerSelector, winData) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;

    const slots = (winData && winData.slots) || [
      { t: "12:00:01", count: 3, state: "expired" },
      { t: "12:00:02", count: 4, state: "active" },
      { t: "12:00:03", count: 2, state: "active" },
      { t: "12:00:04", count: 5, state: "active" },
      { t: "12:00:05", count: 1, state: "new" }
    ];

    const slotsHtml = slots
      .map((s, idx) => `
        <div id="win-slot-${idx}" class="window-slot-box slot-${s.state}">
          <div class="slot-count">${s.count}</div>
          <div class="slot-time">${s.t}</div>
        </div>
      `)
      .join("");

    el.innerHTML = `
      <div class="sliding-win-container">
        <div class="window-header">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">Sliding Window Counter · 滑动窗口限流</div>
          <div class="window-badge">WINDOW</div>
        </div>
        <div class="sliding-win-body">
          <div class="window-timeline-label">1 分钟限流窗口 (Max: 10 req)</div>
          <div class="window-slots-track">
            <div id="sliding-frame" class="sliding-frame"></div>
            ${slotsHtml}
          </div>
          <div id="window-stat-summary" class="window-stat-summary">
            当前窗口总请求数: <span id="win-total-val" class="highlight-val">11</span> (超过阈值 10，触发驳回)
          </div>
        </div>
      </div>
    `;
  }

  function esc(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function mountArray(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;
    const items = (data && data.items) || [];
    const pointers = (data && data.pointers) || [];
    const n = Math.max(items.length, 1);
    const cellW = Math.min(140, Math.floor(820 / n));
    const startX = (936 - cellW * n) / 2;
    const y = 220;
    const cells = items
      .map((it, i) => {
        const x = startX + i * cellW;
        const idx = it.idx != null ? it.idx : i;
        const hl = it.highlight ? "array-cell highlight" : "array-cell";
        return `
        <g id="arr-cell-${idx}" class="${hl}" transform="translate(${x}, ${y})">
          <rect width="${cellW - 8}" height="96" rx="12" fill="#0F172A" stroke="${it.highlight ? "#22C55E" : "#334155"}" stroke-width="3"/>
          <text class="arr-val" x="${(cellW - 8) / 2}" y="48" text-anchor="middle" fill="#F8FAFC" font-size="32" font-weight="800">${esc(it.val)}</text>
          <text x="${(cellW - 8) / 2}" y="82" text-anchor="middle" fill="#64748B" font-size="16">${idx}</text>
          ${it.label ? `<text class="arr-label" x="${(cellW - 8) / 2}" y="-12" text-anchor="middle" fill="#38BDF8" font-size="18" font-weight="700">${esc(it.label)}</text>` : ""}
        </g>`;
      })
      .join("");
    const ptrs = pointers
      .map((p) => {
        const x = startX + (p.target_idx || 0) * cellW + (cellW - 8) / 2;
        return `
        <g id="ptr-${p.name}" class="array-pointer" data-cx="${x}" data-cy="${y + 140}" transform="translate(${x}, ${y + 140})">
          <polygon points="0,0 -10,22 10,22" fill="${p.color || "#10B981"}"/>
          <text y="46" text-anchor="middle" fill="${p.color || "#10B981"}" font-size="18" font-weight="700">${esc(p.name)}</text>
        </g>`;
      })
      .join("");
    el.innerHTML = `<svg class="svg-canvas algo-array" viewBox="0 0 936 560" id="array-svg" data-start-x="${startX}" data-cell-w="${cellW}" data-base-y="${y}">${cells}${ptrs}</svg>`;
  }

  function mountLinkedList(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;
    const nodes = (data && data.nodes) || [];
    const doubly = !data || data.type !== "singly";
    const n = Math.max(nodes.length, 1);
    const boxW = 128;
    const gap = Math.min(48, Math.floor((880 - n * boxW) / Math.max(n - 1, 1)));
    const total = n * boxW + (n - 1) * gap;
    const startX = (936 - total) / 2;
    const y = 210;
    const nodeEls = nodes
      .map((nd, i) => {
        const x = startX + i * (boxW + gap);
        const sent = nd.sentinel;
        const fill = sent ? "#1E293B" : "#0F172A";
        const stroke = sent ? "#64748B" : "#3B82F6";
        const val = nd.val != null ? nd.val : "";
        const key = nd.key != null ? `k=${nd.key}` : "";
        const freq = nd.freq || "";
        return `
        <g id="ll-${nd.id}" class="ll-node${sent ? " sentinel" : ""}" transform="translate(${x}, ${y})" data-index="${i}" data-x="${x}" data-y="${y}">
          <rect class="ll-box" width="${boxW}" height="110" rx="14" fill="${fill}" stroke="${stroke}" stroke-width="3"/>
          <text class="ll-key" x="${boxW / 2}" y="28" text-anchor="middle" fill="#94A3B8" font-size="14">${esc(key)}</text>
          <text class="ll-val" x="${boxW / 2}" y="64" text-anchor="middle" fill="#F8FAFC" font-size="26" font-weight="800">${esc(val)}</text>
          <text class="ll-freq" x="${boxW / 2}" y="92" text-anchor="middle" fill="#F59E0B" font-size="12">${esc(freq)}</text>
        </g>`;
      })
      .join("");
    const edges = nodes
      .slice(0, -1)
      .map((nd, i) => {
        const x1 = startX + i * (boxW + gap) + boxW;
        const x2 = startX + (i + 1) * (boxW + gap);
        const nxt = nodes[i + 1];
        const midY = y + 40;
        const back = doubly
          ? `<line id="ll-e-${nxt.id}-${nd.id}" class="ll-edge ll-back" x1="${x2}" y1="${midY + 28}" x2="${x1}" y2="${midY + 28}" stroke="#64748B" stroke-width="2" marker-end="url(#ll-arrow)"/>`
          : "";
        return `<line id="ll-e-${nd.id}-${nxt.id}" class="ll-edge ll-fwd" x1="${x1}" y1="${midY}" x2="${x2}" y2="${midY}" stroke="#60A5FA" stroke-width="3" marker-end="url(#ll-arrow)"/>${back}`;
      })
      .join("");
    el.innerHTML = `
      <svg class="svg-canvas algo-ll" viewBox="0 0 936 560" id="ll-svg">
        <defs>
          <marker id="ll-arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
            <path d="M0,0 L8,4 L0,8 z" fill="#60A5FA"/>
          </marker>
        </defs>
        ${edges}${nodeEls}
      </svg>`;
  }

  function mountHashMap(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;
    const entries = (data && data.entries) || [];
    const title = (data && data.title) || "HashMap";
    const rows = entries
      .map((e, i) => {
        const hl = e.highlight || e.status === "active" ? "hm-row highlight" : "hm-row";
        return `
        <g id="hm-${esc(e.key)}" class="${hl}" transform="translate(80, ${90 + i * 72})">
          <rect width="776" height="60" rx="10" fill="#0F172A" stroke="#334155" stroke-width="2"/>
          <text x="28" y="38" fill="#38BDF8" font-size="24" font-weight="700" font-family="JetBrains Mono">${esc(e.key)}</text>
          <text x="220" y="38" fill="#64748B" font-size="20">➔</text>
          <text class="hm-val" x="280" y="38" fill="#F8FAFC" font-size="22">${esc(e.val_ref || e.val || "")}</text>
        </g>`;
      })
      .join("");
    el.innerHTML = `
      <svg class="svg-canvas algo-hm" viewBox="0 0 936 560" id="hm-svg">
        <text x="468" y="48" text-anchor="middle" fill="#94A3B8" font-size="22" font-weight="700">${esc(title)}</text>
        ${rows}
      </svg>`;
  }

  function mountTree(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;
    const root = (data && data.root) || { val: "ROOT", children: [] };
    const placed = [];
    function walk(node, depth, x0, x1) {
      const x = (x0 + x1) / 2;
      const y = 70 + depth * 120;
      const id = node.id || node.word || String(node.val);
      placed.push({ node, id, x, y, depth });
      const kids = node.children || [];
      kids.forEach((ch, i) => {
        const span = (x1 - x0) / kids.length;
        walk(ch, depth + 1, x0 + i * span, x0 + (i + 1) * span);
      });
    }
    walk(root, 0, 40, 896);
    const byId = Object.fromEntries(placed.map((p) => [p.id, p]));
    const edges = [];
    function walkE(node) {
      const id = node.id || node.word || String(node.val);
      const p = byId[id];
      (node.children || []).forEach((ch) => {
        const cid = ch.id || ch.word || String(ch.val);
        const c = byId[cid];
        if (p && c) {
          edges.push(`<line class="tree-edge" id="te-${id}-${cid}" x1="${p.x}" y1="${p.y + 28}" x2="${c.x}" y2="${c.y - 28}" stroke="#334155" stroke-width="3"/>`);
        }
        walkE(ch);
      });
    }
    walkE(root);
    const nodes = placed
      .map((p) => {
        const word = p.node.is_word ? ` class="tree-node is-word"` : ` class="tree-node"`;
        return `
        <g id="tree-${p.id}" ${word} transform="translate(${p.x}, ${p.y})">
          <circle r="28" fill="#0F172A" stroke="${p.node.is_word ? "#22C55E" : "#3B82F6"}" stroke-width="3"/>
          <text y="8" text-anchor="middle" fill="#F8FAFC" font-size="18" font-weight="700">${esc(p.node.val)}</text>
          ${p.node.word ? `<text y="52" text-anchor="middle" fill="#86EFAC" font-size="14">${esc(p.node.word)}</text>` : ""}
        </g>`;
      })
      .join("");
    el.innerHTML = `<svg class="svg-canvas algo-tree" viewBox="0 0 936 560" id="tree-svg">${edges.join("")}${nodes}</svg>`;
  }

  function mountStack(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;
    const items = (data && data.items) || [];
    const showTop = !data || data.top_pointer !== false;
    const baseY = 480;
    const boxes = items
      .map((v, i) => {
        const y = baseY - (i + 1) * 72;
        return `
        <g id="stk-${i}" class="stack-item" transform="translate(368, ${y})">
          <rect width="200" height="64" rx="10" fill="#0F172A" stroke="#3B82F6" stroke-width="3"/>
          <text x="100" y="42" text-anchor="middle" fill="#F8FAFC" font-size="26" font-weight="800">${esc(v)}</text>
        </g>`;
      })
      .join("");
    const topY = baseY - items.length * 72 - 36;
    el.innerHTML = `
      <svg class="svg-canvas algo-stack" viewBox="0 0 936 560" id="stack-svg">
        <rect x="360" y="80" width="216" height="410" rx="16" fill="none" stroke="#1E293B" stroke-width="4"/>
        ${boxes}
        ${showTop ? `<g id="stk-top" transform="translate(588, ${topY})"><text fill="#F59E0B" font-size="20" font-weight="700">TOP ⬅</text></g>` : ""}
      </svg>`;
  }

  function mountDpTable(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;
    const rows = (data && data.rows) || [];
    const cols = (data && data.cols) || [];
    const grid = (data && data.grid) || [];
    const active = (data && data.active_cell) || [];
    const cw = 72;
    const ch = 56;
    const ox = 140;
    const oy = 90;
    const colH = cols
      .map((c, j) => `<text x="${ox + (j + 1) * cw + cw / 2}" y="${oy - 16}" text-anchor="middle" fill="#94A3B8" font-size="18">${esc(c)}</text>`)
      .join("");
    const rowH = rows
      .map((r, i) => `<text x="${ox - 16}" y="${oy + (i + 1) * ch + 32}" text-anchor="end" fill="#94A3B8" font-size="18">${esc(r)}</text>`)
      .join("");
    const cells = [];
    grid.forEach((row, i) => {
      (row || []).forEach((v, j) => {
        const isA = active[0] === i && active[1] === j;
        cells.push(`
          <g id="dp-${i}-${j}" class="dp-cell${isA ? " active" : ""}" transform="translate(${ox + (j + 1) * cw}, ${oy + (i + 1) * ch})">
            <rect width="${cw - 6}" height="${ch - 6}" rx="8" fill="${isA ? "#14532D" : "#0F172A"}" stroke="${isA ? "#22C55E" : "#334155"}" stroke-width="2"/>
            <text class="dp-val" x="${(cw - 6) / 2}" y="32" text-anchor="middle" fill="#F8FAFC" font-size="20">${esc(v)}</text>
          </g>`);
      });
    });
    el.innerHTML = `<svg class="svg-canvas algo-dp" viewBox="0 0 936 560" id="dp-svg">${colH}${rowH}${cells.join("")}</svg>`;
  }

  global.AlgoViz = {
    polarToCartesian,
    describeArc,
    mountRing,
    mountBucket,
    mountSlidingWindow,
    mountArray,
    mountLinkedList,
    mountHashMap,
    mountTree,
    mountStack,
    mountDpTable
  };
})(window);
