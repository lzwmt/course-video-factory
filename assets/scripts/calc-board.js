/**
 * CalcBoard - Dynamic Estimation & Back-of-the-envelope Calculation Visualizer
 */
(function (global) {
  function formatFormula(formula) {
    if (!formula) return "";
    // Clean up basic LaTeX frac if present: \frac{a}{b} -> <div class="math-frac"><span class="num">a</span><span class="denom">b</span></div>
    let html = formula;
    html = html.replace(/\\frac\{([^}]+)\}\{([^}]+)\}/g, '<span class="math-frac"><span class="math-num">$1</span><span class="math-denom">$2</span></span>');
    html = html.replace(/\\times/g, "×");
    html = html.replace(/\\approx/g, "≈");
    html = html.replace(/\\text\{([^}]+)\}/g, "$1");
    html = html.replace(/\\cdot/g, "·");
    return html;
  }

  function mountBoard(containerSelector, data) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el || !data) return;

    const title = data.title || "Estimation Calculation";
    const formulaHtml = formatFormula(data.formula || "");
    const steps = data.steps || [];
    const result = data.result || {};

    const stepsHtml = steps
      .map((s, idx) => {
        const hlClass = s.highlight ? "highlight" : "";
        return `
        <div id="calc-step-${idx + 1}" class="calc-step-item ${hlClass}" style="opacity:0; transform: translateY(16px);">
          <div class="calc-step-num">${idx + 1}</div>
          <div class="calc-step-content">
            <div class="calc-step-label">${s.label || ""}</div>
            <div class="calc-step-expr">${s.expr || ""}</div>
          </div>
        </div>`;
      })
      .join("");

    const resultHtml = result.metric
      ? `
      <div id="calc-result-box" class="calc-result-box" style="opacity:0; transform: translateY(16px);">
        <div class="calc-result-header">
          <span class="calc-result-badge">推算结果</span>
          <span class="calc-result-metric">${result.metric}</span>
        </div>
        <div class="calc-result-main">
          <span id="metric-value" class="calc-result-val">${(result.value != null ? result.value : 0).toLocaleString()}</span>
          <span class="calc-result-unit">${result.unit || ""}</span>
        </div>
        ${result.approx ? `<div class="calc-result-approx">约合: ${result.approx}</div>` : ""}
      </div>`
      : "";

    el.innerHTML = `
      <div class="calc-board-container">
        <div class="window-header">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">${title}</div>
          <div class="window-badge">CALCULATION</div>
        </div>
        <div class="calc-board-body">
          ${formulaHtml ? `<div id="calc-formula" class="calc-formula-card" style="opacity:0;"><div class="calc-formula-inner">${formulaHtml}</div></div>` : ""}
          <div class="calc-steps-list">
            ${stepsHtml}
          </div>
          ${resultHtml}
        </div>
      </div>
    `;
  }

  function mountAssumptions(containerSelector, assumptions) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el || !assumptions) return;

    const list = Array.isArray(assumptions) ? assumptions : (assumptions.items || []);
    const cardsHtml = list
      .map((item, idx) => `
        <div id="assumption-card-${idx + 1}" class="assumption-card" style="opacity:0; transform: translateY(20px);">
          <div class="assumption-icon">${item.icon || "📌"}</div>
          <div class="assumption-details">
            <div class="assumption-label">${item.label || item.key || ""}</div>
            <div class="assumption-val">${item.value || item.val || ""}</div>
            ${item.note ? `<div class="assumption-note">${item.note}</div>` : ""}
          </div>
        </div>
      `)
      .join("");

    el.innerHTML = `
      <div class="assumptions-container">
        <div class="assumptions-title">📋 核心基准假设 (Baseline Assumptions)</div>
        <div class="assumptions-grid">
          ${cardsHtml}
        </div>
      </div>
    `;
  }

  function mountUnitsLadder(containerSelector, ladderData) {
    const el = typeof containerSelector === "string" ? document.querySelector(containerSelector) : containerSelector;
    if (!el) return;

    const defaultSteps = [
      { power: "2^10", exact: "1,024 B", approx: "≈ 1 KB", label: "千字节 (Thousand)" },
      { power: "2^20", exact: "1,048,576 B", approx: "≈ 1 MB", label: "兆字节 (Million)" },
      { power: "2^30", exact: "1,073,741,824 B", approx: "≈ 1 GB", label: "吉字节 (Billion)" },
      { power: "2^40", exact: "1,099,511,627,776 B", approx: "≈ 1 TB", label: "太字节 (Trillion)" },
      { power: "2^50", exact: "1,125,899,906,842,624 B", approx: "≈ 1 PB", label: "拍字节 (Petabyte)" }
    ];

    const steps = (ladderData && ladderData.steps) || defaultSteps;
    const stepsHtml = steps
      .map((s, idx) => `
        <div id="ladder-step-${idx + 1}" class="ladder-step-card" style="opacity:0; transform: translateY(16px);">
          <div class="ladder-power">${s.power}</div>
          <div class="ladder-arrow">➜</div>
          <div class="ladder-approx">${s.approx}</div>
          <div class="ladder-label">${s.label}</div>
        </div>
      `)
      .join("");

    el.innerHTML = `
      <div class="units-ladder-container">
        <div class="window-header">
          <div class="window-dots">
            <span class="dot dot-red"></span>
            <span class="dot dot-yellow"></span>
            <span class="dot dot-green"></span>
          </div>
          <div class="window-title">2 的幂次方量级速查表 (Power of 2 Ladder)</div>
          <div class="window-badge">RULES</div>
        </div>
        <div class="ladder-body">
          <div class="ladder-grid">
            ${stepsHtml}
          </div>
        </div>
      </div>
    `;
  }

  global.CalcBoard = {
    mount: mountBoard,
    mountAssumptions: mountAssumptions,
    mountUnitsLadder: mountUnitsLadder
  };
})(window);
