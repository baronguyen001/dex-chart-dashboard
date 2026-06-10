(function () {
  function byId(id) {
    return document.getElementById(id);
  }

  function parseJsonScript(id) {
    const el = byId(id);
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (err) {
      return null;
    }
  }

  function visibleRows(table) {
    return Array.from(table.querySelectorAll("tbody tr")).filter((row) => row.style.display !== "none");
  }

  function setupTableFilters() {
    const table = byId("token-table");
    if (!table) return;
    const search = byId("token-search");
    const chain = byId("chain-filter");
    const count = byId("token-count");

    function apply() {
      const q = (search.value || "").trim().toLowerCase();
      const c = chain.value;
      let shown = 0;
      table.querySelectorAll("tbody tr").forEach((row) => {
        const ok =
          (!q || (row.dataset.text || "").includes(q)) &&
          (!c || row.dataset.chain === c);
        row.style.display = ok ? "" : "none";
        if (ok) shown += 1;
      });
      if (count) count.textContent = `${shown} rows`;
    }

    [search, chain].forEach((el) => {
      if (!el) return;
      el.addEventListener("input", apply);
      el.addEventListener("change", apply);
    });
    apply();
  }

  function setupSorting() {
    document.querySelectorAll("table.data-table").forEach((table) => {
      table.querySelectorAll("th.sortable").forEach((th, index) => {
        th.addEventListener("click", () => {
          const type = th.dataset.type || "text";
          const current = th.dataset.dir === "asc" ? "desc" : "asc";
          table.querySelectorAll("th.sortable").forEach((other) => delete other.dataset.dir);
          th.dataset.dir = current;

          const rows = Array.from(table.querySelectorAll("tbody tr"));
          rows.sort((a, b) => {
            const av = a.children[index]?.dataset.value || a.children[index]?.textContent || "";
            const bv = b.children[index]?.dataset.value || b.children[index]?.textContent || "";
            let result;
            if (type === "number") {
              result = (parseFloat(av) || 0) - (parseFloat(bv) || 0);
            } else {
              result = av.localeCompare(bv);
            }
            return current === "asc" ? result : -result;
          });
          const body = table.querySelector("tbody");
          rows.forEach((row) => body.appendChild(row));
        });
      });
    });
  }

  function setupRefreshPrices() {
    const btn = byId("refresh-prices");
    if (!btn) return;
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      const label = btn.querySelector("span");
      const old = label ? label.textContent : "";
      if (label) label.textContent = "Refreshing…";
      try {
        const response = await fetch("/api/refresh-prices", { method: "POST" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        await response.json();
        window.location.reload();
      } catch (err) {
        if (label) label.textContent = "Refresh failed";
        setTimeout(() => {
          btn.disabled = false;
          if (label) label.textContent = old;
        }, 1200);
      }
    });
  }

  function csvEscape(value) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    if (/[",\n]/.test(text)) {
      return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
  }

  function setupExport() {
    document.querySelectorAll("button[data-table]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const table = byId(btn.dataset.table);
        if (!table) return;
        const headers = Array.from(table.querySelectorAll("thead th")).map((th) => csvEscape(th.textContent));
        const rows = visibleRows(table).map((row) =>
          Array.from(row.children).map((td) => csvEscape(td.textContent)).join(",")
        );
        const csv = [headers.join(","), ...rows].join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${btn.dataset.table}-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
    });
  }

  const UP = "#16a34a";
  const DOWN = "#dc2626";

  function fmtPrice(v) {
    if (v === null || v === undefined) return "-";
    const n = Number(v);
    if (Math.abs(n) >= 1) return n.toFixed(4);
    return n.toPrecision(6);
  }

  // Candlesticks without a plugin: a thin wick bar [low, high] behind a wider body bar
  // [min(o,c), max(o,c)], both centered on the candle (grouped:false so they overlay).
  function buildDatasets(frame) {
    const datasets = [];
    const opens = frame.open || [];
    const highs = frame.high || [];
    const lows = frame.low || [];
    const closes = frame.close || [];

    const isUp = (i) =>
      opens[i] === null || opens[i] === undefined || closes[i] === null || closes[i] >= opens[i];
    const wickColor = closes.map((_, i) => (isUp(i) ? UP : DOWN));
    const bodyFill = closes.map((_, i) => (isUp(i) ? "rgba(22,163,74,0.9)" : "rgba(220,38,38,0.9)"));

    const wick = highs.map((h, i) => {
      const lo = lows[i];
      if (lo === null || lo === undefined || h === null || h === undefined) return null;
      return [lo, h];
    });
    const body = closes.map((c, i) => {
      const o = opens[i];
      if (o === null || o === undefined || c === null || c === undefined) return null;
      return [Math.min(o, c), Math.max(o, c)];
    });

    datasets.push({
      label: "Wick",
      data: wick,
      type: "bar",
      grouped: false,
      backgroundColor: wickColor,
      borderWidth: 0,
      barPercentage: 0.16,
      categoryPercentage: 0.95,
      order: 3,
    });
    datasets.push({
      label: "Price",
      data: body,
      type: "bar",
      grouped: false,
      backgroundColor: bodyFill,
      borderColor: wickColor,
      borderWidth: 1,
      borderSkipped: false,
      minBarLength: 2,
      barPercentage: 0.8,
      categoryPercentage: 0.95,
      order: 1,
      _ohlc: { open: opens, high: highs, low: lows, close: closes },
    });

    const volumes = frame.volume || [];
    if (volumes.some((value) => value !== null && value !== undefined)) {
      datasets.push({
        label: "Volume",
        data: volumes,
        type: "bar",
        yAxisID: "y1",
        grouped: false,
        backgroundColor: "rgba(63, 95, 159, 0.14)",
        borderWidth: 0,
        order: 5,
        barPercentage: 1,
        categoryPercentage: 1,
      });
    }

    function addLevel(label, data, color) {
      if (!data || !data.length) return;
      datasets.push({
        label,
        data,
        type: "line",
        borderColor: color,
        borderDash: [6, 5],
        borderWidth: 1,
        pointRadius: 0,
        tension: 0,
        order: 2,
      });
    }

    addLevel("Entry", frame.levels?.entry, "#0369a1");
    addLevel("SL", frame.levels?.sl, "#b42318");
    addLevel("TP1", frame.levels?.tp1, "#137333");
    addLevel("TP2", frame.levels?.tp2, "#0f766e");
    return datasets;
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: "index" },
    plugins: {
      legend: { position: "bottom", labels: { filter: (item) => item.text !== "Wick" } },
      tooltip: {
        filter: (item) => item.dataset.label !== "Wick",
        callbacks: {
          label: (ctx) => {
            const ds = ctx.dataset;
            if (ds._ohlc) {
              const i = ctx.dataIndex;
              return [
                `O ${fmtPrice(ds._ohlc.open[i])}`,
                `H ${fmtPrice(ds._ohlc.high[i])}`,
                `L ${fmtPrice(ds._ohlc.low[i])}`,
                `C ${fmtPrice(ds._ohlc.close[i])}`,
              ];
            }
            if (ds.yAxisID === "y1") {
              const v = Number(ctx.parsed.y);
              const vol = v >= 1e6 ? `${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}K` : `${v.toFixed(0)}`;
              return `Volume: ${vol}`;
            }
            return `${ds.label}: ${fmtPrice(ctx.parsed.y)}`;
          },
        },
      },
    },
    scales: {
      x: { ticks: { maxTicksLimit: 12 } },
      y: {
        ticks: {
          callback: (value) => {
            const n = Number(value);
            if (Math.abs(n) >= 1) return n.toFixed(4);
            return n.toPrecision(4);
          },
        },
      },
      y1: {
        position: "right",
        beginAtZero: true,
        grid: { drawOnChartArea: false },
        ticks: {
          callback: (value) => {
            const n = Number(value);
            if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
            if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
            return `${n.toFixed(0)}`;
          },
        },
      },
    },
  };

  function renderTokenChart() {
    if (!window.Chart) return;
    const token = parseJsonScript("token-chart-data");
    const tokenEl = byId("token-chart");
    if (!token || !tokenEl) return;

    const frames = token.timeframes || {};
    function frameFor(label) {
      if (label && frames[label]) return frames[label];
      if (token.selected_timeframe && frames[token.selected_timeframe]) {
        return frames[token.selected_timeframe];
      }
      return token; // top-level payload is the selected frame
    }

    let activeChart = null;
    const statusEl = byId("tf-status");

    function renderFrame(label) {
      const frame = frameFor(label);
      if (activeChart) {
        activeChart.destroy();
        activeChart = null;
      }
      activeChart = new Chart(tokenEl, {
        type: "bar",
        data: { labels: frame.labels || [], datasets: buildDatasets(frame) },
        options: chartOptions,
      });
      if (statusEl) {
        statusEl.textContent = `${frame.timeframe} candles (${(frame.labels || []).length})`;
      }
    }

    renderFrame(token.selected_timeframe);

    document.querySelectorAll("#tf-switch .tf-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.disabled) return;
        const label = btn.dataset.timeframe;
        if (!frames[label]) return;
        document.querySelectorAll("#tf-switch .tf-btn").forEach((other) => other.classList.remove("active"));
        btn.classList.add("active");
        renderFrame(label);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupTableFilters();
    setupSorting();
    setupRefreshPrices();
    setupExport();
    renderTokenChart();
  });
})();
