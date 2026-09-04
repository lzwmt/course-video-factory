(function (global) {
  const NODES = {
    client: { x: 80, y: 80, w: 160, h: 72, label: "Client", fill: "#1e3a5f" },
    lb: { x: 340, y: 80, w: 200, h: 72, label: "Load Balancer", fill: "#1e40af" },
    web: { x: 620, y: 40, w: 240, h: 150, label: "Web Cluster", fill: "#164e63", sub: "stateless" },
    redis: { x: 340, y: 280, w: 200, h: 80, label: "Redis Cache", fill: "#14532d" },
    mysql: { x: 620, y: 280, w: 240, h: 80, label: "MySQL", fill: "#7c2d12" },
    mq: { x: 80, y: 420, w: 200, h: 80, label: "Message Queue", fill: "#78350f" },
    worker: { x: 340, y: 420, w: 200, h: 80, label: "Worker", fill: "#3f3f46" },
    single: { x: 280, y: 180, w: 360, h: 160, label: "Single Server", fill: "#7f1d1d", sub: "Web + MySQL" },
  };

  const ALIAS = {
    web_nodes: "web",
    mysql_primary: "mysql",
    single_box: "single",
    server: "single",
    user: "client",
    cache: "redis",
  };

  const EDGE_COLOR = {
    blue: "#3B82F6",
    green: "#22C55E",
    red: "#EF4444",
    orange: "#F59E0B",
  };

  function resolveId(id) {
    return ALIAS[id] || id;
  }

  function centerOf(id) {
    const n = NODES[resolveId(id)];
    if (!n) return { x: 468, y: 280 };
    return { x: n.x + n.w / 2, y: n.y + n.h / 2 };
  }

  function nodeSvg(id) {
    const n = NODES[id];
    const sub = n.sub
      ? `<text x="${n.x + n.w / 2}" y="${n.y + 52}" text-anchor="middle" fill="#94a3b8" font-size="16">${n.sub}</text>`
      : "";
    return `<g id="node-${id}" class="node-box" opacity="0">
      <rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="14" fill="${n.fill}" stroke="#94a3b8" stroke-width="2"/>
      <text x="${n.x + n.w / 2}" y="${n.y + 32}" text-anchor="middle" fill="#f8fafc" font-size="22" font-weight="700">${n.label}</text>
      ${sub}
    </g>`;
  }

  function edgeSvg(from, to, colorName) {
    const a = centerOf(from);
    const b = centerOf(to);
    const color = EDGE_COLOR[colorName] || EDGE_COLOR.blue;
    const id = `e-${resolveId(from)}-${resolveId(to)}`;
    return `<line id="${id}" class="graph-edge" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${color}" stroke-width="3" opacity="0"/>`;
  }

  function mount(svgSelector, graph) {
    const svg = typeof svgSelector === "string" ? document.querySelector(svgSelector) : svgSelector;
    if (!svg) return;
    const nodes = (graph && graph.nodes) || [];
    const edges = (graph && graph.edges) || [];
    const parts = [];
    edges.forEach((e) => {
      if (Array.isArray(e)) parts.push(edgeSvg(e[0], e[1], e[2]));
      else parts.push(edgeSvg(e.from, e.to, e.color));
    });
    nodes.map(resolveId).forEach((id) => {
      if (NODES[id]) parts.push(nodeSvg(id));
    });
    parts.push('<circle id="pkt" r="8" fill="#3B82F6" opacity="0"/>');
    svg.innerHTML = parts.join("");
  }

  global.ArchGraph = { NODES, ALIAS, resolveId, centerOf, mount };
})(window);
