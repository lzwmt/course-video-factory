(function (global) {
  const COLOR = { blue: "#3B82F6", green: "#22C55E", red: "#EF4444", orange: "#F59E0B" };

  function nid(id) {
    const r = global.ArchGraph ? ArchGraph.resolveId(id) : id;
    return `#node-${r}`;
  }
  function eid(from, to) {
    const a = global.ArchGraph ? ArchGraph.resolveId(from) : from;
    const b = global.ArchGraph ? ArchGraph.resolveId(to) : to;
    return `#e-${a}-${b}`;
  }
  function sel(target) {
    if (!target) return null;
    const s = String(target);
    if (s.startsWith("#") || s.startsWith(".")) return s;
    return nid(s);
  }

  function playActions(tl, actions, startAt) {
    let t = startAt || 0.5;
    let cardCount = 0;
    (actions || []).forEach((act, i) => {
      const at = act.at != null ? act.at : t;
      const type = act.type;

      // --- Base & Motion Actions ---
      if (type === "enter") {
        const target = sel(act.target || act.id);
        if (target && global.motion) tl.add(motion.enter(target, { y: 12, scale: 1 }), at);
      } else if (type === "add_node" || type === "node") {
        tl.to(nid(act.target || act.id), { attr: { opacity: 1 }, duration: 0.35, ease: "none" }, at);
      } else if (type === "reveal_graph") {
        const dur = act.instant ? 0.01 : 0.3;
        tl.to(".node-box", { attr: { opacity: 1 }, stagger: act.instant ? 0 : 0.08, duration: dur, ease: "none" }, at);
        tl.to(".graph-edge", { attr: { opacity: 1 }, stagger: act.instant ? 0 : 0.06, duration: dur, ease: "none" }, at + (act.instant ? 0 : 0.2));
      } else if (type === "connect") {
        const edge = eid(act.from, act.to);
        tl.to(edge, { attr: { opacity: 1 }, duration: 0.3, ease: "none" }, at);
        if (global.motion && motion.connect) tl.add(motion.connect(edge, { duration: 0.45 }), at);
      } else if (type === "packet") {
        if (global.ArchGraph) {
          const fromC = ArchGraph.centerOf(act.from);
          const toC = ArchGraph.centerOf(act.to);
          const color = COLOR[act.color] || COLOR.blue;
          tl.add(motion.packet("#pkt", fromC, toC, { color, duration: 0.7 }), at);
        }
      } else if (type === "highlight") {
        tl.to(nid(act.target) + " rect", { stroke: "#22C55E", duration: 0.35 }, at);
        tl.to(nid(act.target), { attr: { opacity: 1 }, duration: 0.2 }, at);
      } else if (type === "metric") {
        const bar = act.target === "io" ? "#io-bar" : "#cpu-bar";
        const val = act.target === "io" ? "#io-val" : "#cpu-val";
        tl.add(motion.metricBar(bar, act.value || 100), at);
        tl.add(motion.counter(val, 0, act.value || 100, { suffix: "%" }), at);
      } else if (type === "counter") {
        tl.add(motion.counter(act.target || "#counter", act.from || 0, act.to || 10000), at);
      } else if (type === "alert") {
        tl.add(motion.enter("#alert-box"), at);
        tl.add(motion.shake("#alert-box"), at + 0.15);
      } else if (type === "zoom") {
        tl.add(motion.zoom(act.container || "#topo", { scale: act.scale || 1.12, duration: 0.6 }), at);
      } else if (type === "focus") {
        tl.add(motion.focus(nid(act.target), { others: ".node-box" }), at);
        tl.add(motion.zoom("#topo", { scale: act.scale || 1.1, duration: 0.55 }), at);
      } else if (type === "code_line") {
        tl.to(".code-line", { opacity: 0.35, duration: 0.2 }, at);
        tl.to(`#code-line-${act.index}`, { opacity: 1, scale: 1.04, duration: 0.25 }, at);
      } else if (type === "term_line") {
        tl.to(`#term-line-${act.index}`, { opacity: 1, duration: 0.2 }, at);
      } else if (type === "card") {
        cardCount++;
        const idx = act.index != null ? act.index : cardCount;
        tl.add(motion.enter(`#rule${idx}`), at);
      } else if (type === "split_node" || type === "scale_node") {
        tl.to(".node-box", { attr: { opacity: 1 }, stagger: 0.1, duration: 0.3, ease: "none" }, at);
        tl.to(".graph-edge", { attr: { opacity: 1 }, stagger: 0.08, duration: 0.25, ease: "none" }, at + 0.25);
      }

      // --- Template B: CalcBoard & Estimation Actions ---
      else if (type === "calc_show_step" || type === "show_step") {
        const stepTarget = `#calc-step-${act.index}`;
        tl.to(stepTarget, { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, at);
        if (act.highlight) {
          tl.to(stepTarget, { borderColor: "#3B82F6", duration: 0.3 }, at + 0.15);
        }
      } else if (type === "calc_roll_result" || type === "roll_result") {
        tl.to("#calc-result-box", { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, at);
        const fromVal = act.from != null ? act.from : 0;
        const toVal = act.to != null ? act.to : 10000;
        tl.add(motion.counter(act.target || "#metric-value", fromVal, toVal, { duration: act.duration || 0.8 }), at + 0.1);
        tl.add(motion.pulse("#calc-result-box", { duration: 0.35, scale: 1.04, repeat: 1 }), at + 0.85);
      } else if (type === "calc_show_formula" || type === "show_formula") {
        tl.to("#calc-formula", { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" }, at);
      } else if (type === "calc_show_assumption" || type === "show_assumption" || type === "assumption_card") {
        tl.to(`#assumption-card-${act.index}`, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, at);
      } else if (type === "calc_show_ladder" || type === "show_ladder" || type === "ladder_step") {
        tl.to(`#ladder-step-${act.index}`, { opacity: 1, y: 0, duration: 0.35, ease: "power2.out" }, at);
      }

      // --- Template C: AlgoViz & Algorithm Actions ---
      else if (type === "ring_init") {
        tl.to("#ring-glow-track", { opacity: 1, duration: 0.5 }, at);
        tl.to(".ring-node-group", { opacity: 1, stagger: 0.1, duration: 0.4 }, at + 0.2);
        tl.to(".ring-vnode-group", { opacity: 1, stagger: 0.05, duration: 0.3 }, at + 0.4);
      } else if (type === "ring_route") {
        if (global.AlgoViz) {
          const angle = act.angle != null ? act.angle : 45;
          const p = AlgoViz.polarToCartesian(468, 280, 210, angle);
          tl.set("#ring-key-circle", { attr: { cx: p.x, cy: p.y } }, at);
          tl.set("#ring-key-text", { attr: { x: p.x, y: p.y - 20 }, innerText: act.key || "Key" }, at);
          tl.to("#ring-key-spot", { opacity: 1, duration: 0.25 }, at);
          if (act.target_node) {
            const targetSel = `#ring-${act.target_node.toLowerCase()}`;
            tl.to(`${targetSel} .ring-node-circle`, { stroke: "#22C55E", strokeWidth: 5, duration: 0.35 }, at + 0.3);
            tl.add(motion.pulse(targetSel, { scale: 1.12, duration: 0.3, repeat: 1 }), at + 0.45);
          }
        }
      } else if (type === "ring_node_down") {
        const targetSel = `#ring-${(act.target_node || act.target || "node_2").toLowerCase()}`;
        tl.to(`${targetSel} .ring-node-circle`, { stroke: "#EF4444", strokeWidth: 5, fill: "#450a0a", duration: 0.35 }, at);
        tl.to(targetSel, { opacity: 0.6, duration: 0.35 }, at);
        tl.add(motion.shake(targetSel), at + 0.1);
      } else if (type === "ring_add_node") {
        const targetSel = `#ring-${(act.target_node || act.target || "node_4").toLowerCase()}`;
        tl.to(targetSel, { opacity: 1, scale: 1.15, duration: 0.4 }, at);
        tl.to(targetSel, { scale: 1, duration: 0.2 }, at + 0.4);
      } else if (type === "bucket_refill") {
        tl.fromTo("#token-drop-particle", { opacity: 1, y: 0 }, { opacity: 0, y: 50, duration: 0.35, ease: "power1.in" }, at);
        tl.to("#bucket-water", { height: `${act.level || 75}%`, duration: 0.35 }, at + 0.35);
        if (act.count != null) {
          tl.set("#token-count-val", { innerText: String(act.count) }, at + 0.35);
        }
      } else if (type === "bucket_consume") {
        tl.to("#req-pkt-1", { opacity: 1, duration: 0.25 }, at);
        tl.to("#bucket-water", { height: `${act.level || 50}%`, duration: 0.3 }, at + 0.25);
        if (act.count != null) {
          tl.set("#token-count-val", { innerText: String(act.count) }, at + 0.25);
        }
        tl.to("#gate-decision-box", { opacity: 1, duration: 0.2 }, at + 0.35);
      } else if (type === "bucket_reject") {
        tl.to("#req-pkt-3", { opacity: 1, duration: 0.2 }, at);
        tl.add(motion.shake("#req-pkt-3"), at + 0.15);
        tl.to("#gate-decision-box", { opacity: 1, duration: 0.2 }, at + 0.2);
        tl.set("#gate-status-text", { className: "status-reject", innerText: "REJECT 429: 令牌耗尽，触发限流驳回" }, at + 0.2);
      } else if (type === "window_slide") {
        const dist = act.x != null ? act.x : 140;
        tl.to("#sliding-frame", { x: dist, duration: 0.65, ease: "power2.inOut" }, at);
        tl.to("#win-slot-0", { opacity: 0.35, scale: 0.95, duration: 0.35 }, at + 0.2);
        tl.to("#win-slot-0 .slot-count", { color: "#64748B", duration: 0.3 }, at + 0.2);
        tl.to("#win-slot-4", { borderColor: "#22C55E", duration: 0.35 }, at + 0.3);
        tl.to("#window-stat-summary", { opacity: 1, duration: 0.35 }, at + 0.45);
        if (global.motion && motion.pulse) tl.add(motion.pulse("#window-stat-summary", { scale: 1.05, duration: 0.3, repeat: 1 }), at + 0.55);
      } else if (type === "move_pointer") {
        const svg = document.querySelector("#array-svg");
        const cell = document.querySelector(`#arr-cell-${act.to_idx}`);
        const ptr = document.querySelector(`#ptr-${act.name}`);
        if (svg && cell && ptr) {
          const cellW = parseFloat(svg.getAttribute("data-cell-w") || "120");
          const ct = cell.getAttribute("transform") || "";
          const cm = /translate\(([^,]+),\s*([^)]+)\)/.exec(ct);
          const destX = cm ? parseFloat(cm[1]) + (cellW - 8) / 2 : parseFloat(ptr.getAttribute("data-cx") || "0");
          const cy = parseFloat(ptr.getAttribute("data-cy") || "360");
          const fromX = parseFloat(ptr.getAttribute("data-cx") || destX);
          const proxy = { x: fromX };
          tl.to(proxy, {
            x: destX,
            duration: 0.45,
            ease: "power2.inOut",
            onUpdate: function () {
              ptr.setAttribute("transform", `translate(${proxy.x}, ${cy})`);
            },
            onComplete: function () {
              ptr.setAttribute("data-cx", String(destX));
            }
          }, at);
        }
      } else if (type === "highlight_item") {
        const selCell = `#arr-cell-${act.index} rect`;
        tl.to(selCell, { stroke: act.cls === "active" ? "#22C55E" : "#F59E0B", duration: 0.3 }, at);
        if (global.motion) tl.add(motion.pulse(`#arr-cell-${act.index}`, { scale: 1.06, duration: 0.25, repeat: 1 }), at);
      } else if (type === "detach_node") {
        const tsel = `#ll-${act.target}`;
        tl.to(`${tsel} .ll-box`, { stroke: "#F59E0B", duration: 0.2 }, at);
        tl.to(tsel, { y: -56, duration: 0.4, ease: "power2.out" }, at + 0.1);
        document.querySelectorAll(".ll-edge").forEach((e) => {
          const id = e.id || "";
          if (id.includes(`-${act.target}`) || id.includes(`${act.target}-`)) {
            tl.to(e, { opacity: 0, duration: 0.25 }, at);
          }
        });
      } else if (type === "insert_head") {
        const tsel = `#ll-${act.target}`;
        const node = document.querySelector(tsel);
        const afterId = act.after || "head";
        const after = document.querySelector(`#ll-${afterId}`);
        if (node && after) {
          const nx = parseFloat(node.getAttribute("data-x") || "0");
          const ax = parseFloat(after.getAttribute("data-x") || "0");
          const slot = ax + 128 + 24;
          tl.to(tsel, { y: 0, x: slot - nx, duration: 0.5, ease: "power2.inOut" }, at);
          document.querySelectorAll(".ll-node").forEach((el) => {
            if (el.id === `ll-${act.target}` || el.id === `ll-${afterId}`) return;
            const ix = parseFloat(el.getAttribute("data-x") || "0");
            if (ix >= slot - 8 && ix < nx) {
              tl.to(el, { x: 40, duration: 0.45, ease: "power2.inOut" }, at);
            }
          });
        } else {
          tl.to(tsel, { y: 0, x: act.dx || -40, duration: 0.45, ease: "power2.inOut" }, at);
        }
        tl.to(`${tsel} .ll-box`, { stroke: "#22C55E", duration: 0.25 }, at + 0.3);
        tl.to(".ll-edge", { opacity: 1, duration: 0.3 }, at + 0.4);
      } else if (type === "remove_tail") {
        const tsel = `#ll-${act.target}`;
        tl.to(tsel, { opacity: 0, y: 48, duration: 0.4 }, at);
        document.querySelectorAll(".ll-edge").forEach((e) => {
          const id = e.id || "";
          if (id.includes(act.target)) tl.to(e, { opacity: 0, duration: 0.25 }, at);
        });
      } else if (type === "map_put") {
        tl.to(`#hm-${act.key}`, { opacity: 1, duration: 0.3 }, at);
        tl.to(`#hm-${act.key} rect`, { stroke: "#22C55E", duration: 0.25 }, at);
      } else if (type === "map_highlight") {
        tl.to(`#hm-${act.key} rect`, { stroke: "#22C55E", duration: 0.3 }, at);
      } else if (type === "map_delete") {
        tl.to(`#hm-${act.key}`, { opacity: 0.2, duration: 0.35 }, at);
      } else if (type === "traverse_path") {
        (act.path || []).forEach((p, i) => {
          tl.to(`#tree-${p} circle`, { stroke: "#F59E0B", duration: 0.25 }, at + i * 0.25);
          if (global.motion) tl.add(motion.pulse(`#tree-${p}`, { scale: 1.08, duration: 0.2, repeat: 0 }), at + i * 0.25);
        });
      } else if (type === "pulse_node") {
        const tsel = `#tree-${act.target}`;
        if (global.motion) tl.add(motion.pulse(tsel, { scale: 1.12, duration: 0.3, repeat: 1 }), at);
      } else if (type === "push_stack") {
        const svg = document.querySelector("#stack-svg");
        const items = document.querySelectorAll(".stack-item");
        const val = act.val != null ? act.val : 0;
        if (svg) {
          const i = items.length;
          const y = 480 - (i + 1) * 72;
          const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
          g.setAttribute("id", `stk-${i}`);
          g.setAttribute("class", "stack-item");
          g.setAttribute("transform", `translate(368, ${y})`);
          g.innerHTML = `<rect width="200" height="64" rx="10" fill="#0F172A" stroke="#22C55E" stroke-width="3"/><text x="100" y="42" text-anchor="middle" fill="#F8FAFC" font-size="26" font-weight="800">${val}</text>`;
          svg.appendChild(g);
          tl.fromTo(g, { opacity: 0, y: -40 }, { opacity: 1, y: 0, duration: 0.35 }, at);
        }
        tl.to("#stk-top", { y: "-=72", duration: 0.3 }, at);
      } else if (type === "pop_stack") {
        const items = document.querySelectorAll(".stack-item");
        const last = items[items.length - 1];
        if (last) tl.to(last, { opacity: 0, y: -28, duration: 0.3 }, at);
        tl.to("#stk-top", { y: "+=72", duration: 0.3 }, at);
      } else if (type === "fill_cell") {
        (act.from || []).forEach((pair, i) => {
          tl.to(`#dp-${pair[0]}-${pair[1]} rect`, { stroke: "#F59E0B", duration: 0.25 }, at + i * 0.12);
        });
        const cell = `#dp-${act.row}-${act.col} .dp-val`;
        tl.set(cell, { innerHTML: String(act.val) }, at + 0.25);
        tl.to(`#dp-${act.row}-${act.col} rect`, { stroke: "#22C55E", fill: "#14532D", duration: 0.3 }, at + 0.25);
      } else {
        if (typeof console !== "undefined" && console.warn) {
          console.warn("[playActions] unknown type", type, act);
        }
        const low = String(type || "");
        if (/ring/i.test(low)) {
          tl.to("#ring-glow-track", { opacity: 1, duration: 0.4 }, at);
          tl.to(".ring-node-group", { opacity: 1, stagger: 0.08, duration: 0.35 }, at + 0.15);
        } else if (/formula|calc/i.test(low)) {
          tl.to("#calc-formula", { opacity: 1, y: 0, duration: 0.35 }, at);
        } else if (document.querySelector(".node-box")) {
          tl.to(".node-box", { attr: { opacity: 1 }, stagger: 0.08, duration: 0.3, ease: "none" }, at);
          tl.to(".graph-edge", { attr: { opacity: 1 }, stagger: 0.06, duration: 0.25, ease: "none" }, at + 0.15);
        } else {
          const fallback = sel(act.target || act.id) || "#title";
          if (global.motion) tl.add(motion.enter(fallback, { y: 12, scale: 1 }), at);
        }
      }

      t = at + 0.45;
    });
    return tl;
  }

  global.playActions = playActions;
})(window);
