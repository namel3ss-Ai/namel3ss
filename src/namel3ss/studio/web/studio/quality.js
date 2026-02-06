(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const quality = root.quality || (root.quality = {});

  function row(text) {
    const div = document.createElement("div");
    div.className = "status-line";
    div.textContent = text;
    return div;
  }

  function issueRow(item) {
    const div = document.createElement("div");
    div.className = "list-item";
    div.textContent = `${item.code} ${item.entity} ${item.issue}`;
    return div;
  }

  async function renderQuality() {
    const panel = document.getElementById("quality");
    if (!panel) return;
    panel.innerHTML = "";

    const stack = document.createElement("div");
    stack.className = "panel-stack";

    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Quality gates";
    const refreshBtn = document.createElement("button");
    refreshBtn.className = "btn ghost";
    refreshBtn.textContent = "Refresh";
    const fixesBtn = document.createElement("button");
    fixesBtn.className = "btn ghost";
    fixesBtn.textContent = "Suggest fixes";
    const actions = document.createElement("div");
    actions.className = "ui-buttons";
    actions.appendChild(refreshBtn);
    actions.appendChild(fixesBtn);
    header.appendChild(title);
    header.appendChild(actions);

    const summary = document.createElement("div");
    summary.className = "panel-section";
    const summaryTitle = document.createElement("div");
    summaryTitle.className = "panel-section-title";
    summaryTitle.textContent = "Summary";
    const lines = document.createElement("div");
    lines.className = "status-lines";
    summary.appendChild(summaryTitle);
    summary.appendChild(lines);

    const fixesSection = document.createElement("div");
    fixesSection.className = "panel-section";
    const fixesTitle = document.createElement("div");
    fixesTitle.className = "panel-section-title";
    fixesTitle.textContent = "Fix suggestions";
    const fixesList = document.createElement("div");
    fixesList.className = "status-lines";
    fixesSection.appendChild(fixesTitle);
    fixesSection.appendChild(fixesList);

    const issuesSection = document.createElement("div");
    issuesSection.className = "panel-section";
    const issuesTitle = document.createElement("div");
    issuesTitle.className = "panel-section-title";
    issuesTitle.textContent = "Issues";
    const issuesList = document.createElement("div");
    issuesList.className = "list";
    issuesSection.appendChild(issuesTitle);
    issuesSection.appendChild(issuesList);

    stack.appendChild(header);
    stack.appendChild(summary);
    stack.appendChild(fixesSection);
    stack.appendChild(issuesSection);
    panel.appendChild(stack);

    async function render(payload) {
      lines.innerHTML = "";
      fixesList.innerHTML = "";
      issuesList.innerHTML = "";

      lines.appendChild(row(`ok ${payload.ok}`));
      lines.appendChild(row(`issues ${payload.count || 0}`));

      const issues = payload && Array.isArray(payload.issues) ? payload.issues : [];
      if (!issues.length) {
        issuesList.appendChild(dom.buildEmpty("No quality issues."));
      } else {
        issues.forEach((item) => issuesList.appendChild(issueRow(item)));
      }

      const fixes = payload && Array.isArray(payload.fixes) ? payload.fixes : [];
      if (!fixes.length) {
        fixesList.appendChild(row("No fix suggestions."));
      } else {
        fixes.forEach((item) => fixesList.appendChild(row(String(item))));
      }
    }

    async function runCheck() {
      const payload = await net.fetchJson("/api/quality");
      await render(payload);
    }

    async function runFixes() {
      const payload = await net.postJson("/api/quality", { action: "fix" });
      await render(payload);
    }

    refreshBtn.addEventListener("click", () => runCheck());
    fixesBtn.addEventListener("click", () => runFixes());

    try {
      await runCheck();
    } catch (err) {
      panel.innerHTML = "";
      dom.showError(panel, err && err.message ? err.message : "Quality panel failed.");
    }
  }

  quality.renderQuality = renderQuality;
})();
