(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function formatValue(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "number") return String(value);
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  function chartTitle(chartType) {
    if (chartType === "bar") return "Bar chart";
    if (chartType === "line") return "Line chart";
    return "Summary";
  }

  function renderChartElement(el) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element";

    const chartType = el.chart_type || "summary";
    const chart = document.createElement("div");
    chart.className = `ui-chart ui-chart-${chartType}`;

    const header = document.createElement("div");
    header.className = "ui-chart-header";
    const title = document.createElement("div");
    title.className = "ui-chart-title";
    title.textContent = chartTitle(chartType);
    header.appendChild(title);

    if (el.explain) {
      const explain = document.createElement("div");
      explain.className = "ui-chart-explain";
      explain.textContent = el.explain;
      header.appendChild(explain);
    }

    const metaParts = [];
    if (el.record) metaParts.push(`record: ${el.record}`);
    if (el.source) metaParts.push(`source: ${el.source}`);
    if (el.x) metaParts.push(`x: ${el.x}`);
    if (el.y) metaParts.push(`y: ${el.y}`);
    if (metaParts.length) {
      const meta = document.createElement("div");
      meta.className = "ui-chart-meta";
      meta.textContent = metaParts.join(" \u2022 ");
      header.appendChild(meta);
    }

    chart.appendChild(header);

    if (chartType === "summary") {
      const summary = el.summary || {};
      const items = [
        { label: "Count", value: summary.count },
        { label: "Total", value: summary.total },
        { label: "Average", value: summary.average },
      ];
      const summaryWrap = document.createElement("div");
      summaryWrap.className = "ui-chart-summary";
      items.forEach((item) => {
        if (item.value === undefined) return;
        const block = document.createElement("div");
        block.className = "ui-chart-summary-item";
        const label = document.createElement("div");
        label.className = "ui-chart-summary-label";
        label.textContent = item.label;
        const value = document.createElement("div");
        value.className = "ui-chart-summary-value";
        value.textContent = formatValue(item.value);
        block.appendChild(label);
        block.appendChild(value);
        summaryWrap.appendChild(block);
      });
      if (!summaryWrap.children.length) {
        const empty = document.createElement("div");
        empty.className = "ui-chart-empty";
        empty.textContent = "No summary available.";
        summaryWrap.appendChild(empty);
      }
      chart.appendChild(summaryWrap);
      wrapper.appendChild(chart);
      return wrapper;
    }

    const series = Array.isArray(el.series) ? el.series : [];
    if (!series.length) {
      const empty = document.createElement("div");
      empty.className = "ui-chart-empty";
      empty.textContent = "No chart data.";
      chart.appendChild(empty);
      wrapper.appendChild(chart);
      return wrapper;
    }

    const maxY = series.reduce((max, entry) => {
      const value = typeof entry.y === "number" ? Math.abs(entry.y) : 0;
      return Math.max(max, value);
    }, 0);
    const seriesWrap = document.createElement("div");
    seriesWrap.className = "ui-chart-series";
    series.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "ui-chart-row";
      const label = document.createElement("div");
      label.className = "ui-chart-label";
      label.textContent = formatValue(entry.x);
      const bar = document.createElement("div");
      bar.className = "ui-chart-bar";
      const fill = document.createElement("div");
      fill.className = "ui-chart-bar-fill";
      const yValue = typeof entry.y === "number" ? entry.y : 0;
      const width = maxY > 0 ? Math.min(100, (Math.abs(yValue) / maxY) * 100) : 0;
      fill.style.width = `${width}%`;
      bar.appendChild(fill);
      const value = document.createElement("div");
      value.className = "ui-chart-value";
      value.textContent = formatValue(entry.y);
      row.appendChild(label);
      row.appendChild(bar);
      row.appendChild(value);
      seriesWrap.appendChild(row);
    });
    chart.appendChild(seriesWrap);
    wrapper.appendChild(chart);
    return wrapper;
  }

  root.renderChartElement = renderChartElement;
})();
