(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderSummary(data) {
    state.setCachedSummary(data || {});
    const container = document.getElementById("summary");
    if (!container) return;
    container.innerHTML = "";
    if (!data || data.ok === false) {
      utils.showEmpty(container, data && data.error ? data.error : "Unable to load summary");
      utils.updateCopyButton("summaryCopy", () => "");
      return;
    }
    utils.setFileName(data.file);
    const counts = data.counts || {};
    const kv = document.createElement("div");
    kv.className = "key-values";
    Object.keys(counts).forEach((key) => {
      const row = document.createElement("div");
      row.className = "kv-row";
      row.innerHTML = `<div class=\"kv-label\">${key}</div><div class=\"kv-value\">${counts[key]}</div>`;
      kv.appendChild(row);
    });
    const manifest = state.getCachedManifest();
    if (manifest && manifest.theme) {
      const setting = manifest.theme.setting || "system";
      const runtime = manifest.theme.current || setting;
      const display = state.getThemeOverride() || runtime;
      const effective = resolveTheme(display);
      const tokenMap = applyThemeTokens(manifest.theme.tokens || {}, display);
      const row = document.createElement("div");
      row.className = "kv-row";
      const overrideLabel = state.getThemeOverride() ? " (preview override)" : "";
      row.innerHTML = `<div class=\"kv-label\">theme</div><div class=\"kv-value\">setting: ${setting}, engine: ${runtime}, effective: ${effective}${overrideLabel}</div>`;
      kv.appendChild(row);
      const tokensRow = document.createElement("div");
      tokensRow.className = "kv-row";
      tokensRow.innerHTML = `<div class=\"kv-label\">tokens</div><div class=\"kv-value\">${JSON.stringify(tokenMap)}</div>`;
      kv.appendChild(tokensRow);
      const pref = manifest.theme.preference || {};
      const prefRow = document.createElement("div");
      prefRow.className = "kv-row";
      prefRow.innerHTML = `<div class=\"kv-label\">preference</div><div class=\"kv-value\">allow_override: ${pref.allow_override ? "true" : "false"}, persist: ${pref.persist || "none"}</div>`;
      kv.appendChild(prefRow);
    }
    container.appendChild(kv);
    if (data.module_summary) {
      container.appendChild(renderModuleSummary(data.module_summary));
    }
    if (data.graduation) {
      container.appendChild(renderGraduationSummary(data.graduation));
    }
    utils.updateCopyButton("summaryCopy", () => JSON.stringify(data, null, 2));
  }

  function renderModuleSummary(summary) {
    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Modules";
    section.appendChild(title);

    const body = document.createElement("div");
    body.className = "module-summary";
    const modules = Array.isArray(summary.modules) ? summary.modules : [];
    if (!modules.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "No modules loaded";
      body.appendChild(empty);
      section.appendChild(body);
      return section;
    }

    const mergeOrder = Array.isArray(summary.merge_order) ? summary.merge_order : [];
    if (mergeOrder.length) {
      const line = document.createElement("div");
      line.textContent = `merge order: ${mergeOrder.join(", ")}`;
      body.appendChild(line);
    }

    modules.forEach((module) => {
      const alias = module.module_alias || module.module_name || "module";
      const path = module.module_id || module.path || "";
      const header = document.createElement("div");
      header.textContent = `module ${alias} from ${path}`;
      body.appendChild(header);
      const provided = module.provided || {};
      Object.keys(provided)
        .sort()
        .forEach((key) => {
          const names = provided[key] || [];
          if (!names.length) return;
          const line = document.createElement("div");
          line.textContent = `provides ${key}: ${names.join(", ")}`;
          body.appendChild(line);
        });
    });

    const overrides = Array.isArray(summary.overrides) ? summary.overrides : [];
    const overrideHeader = document.createElement("div");
    overrideHeader.textContent = overrides.length ? "overrides" : "no overrides";
    body.appendChild(overrideHeader);
    overrides.forEach((entry) => {
      const prev = entry.previous?.origin === "module" ? `module ${entry.previous.module_alias}` : "main file";
      const line = document.createElement("div");
      line.textContent = `${entry.kind} ${entry.name} overridden by module ${entry.current.module_alias}, was from ${prev}`;
      body.appendChild(line);
    });

    section.appendChild(body);
    return section;
  }

  function renderGraduationSummary(data) {
    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Graduation";
    section.appendChild(title);

    const body = document.createElement("div");
    body.className = "graduation-summary";
    const summaryLines = Array.isArray(data.summary_lines) ? data.summary_lines : [];
    const graduationLines = Array.isArray(data.graduation_lines) ? data.graduation_lines : [];
    if (!summaryLines.length && !graduationLines.length) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "No graduation data";
      body.appendChild(empty);
      section.appendChild(body);
      return section;
    }
    summaryLines.concat(graduationLines).forEach((line) => {
      const row = document.createElement("div");
      row.textContent = line;
      body.appendChild(row);
    });

    const items = Array.isArray(data.capabilities) ? data.capabilities : [];
    if (items.length) {
      const proofTitle = document.createElement("div");
      proofTitle.textContent = "Proof links";
      body.appendChild(proofTitle);
      items
        .filter((item) => item.status === "shipped")
        .forEach((item) => {
          const header = document.createElement("div");
          header.textContent = `capability ${item.id}`;
          body.appendChild(header);
          const tests = Array.isArray(item.tests) ? item.tests : [];
          const examples = Array.isArray(item.examples) ? item.examples : [];
          if (tests.length) {
            const line = document.createElement("div");
            line.textContent = `tests ${tests.join(", ")}`;
            body.appendChild(line);
          }
          if (examples.length) {
            const line = document.createElement("div");
            line.textContent = `examples ${examples.join(", ")}`;
            body.appendChild(line);
          }
        });
    }
    section.appendChild(body);
    return section;
  }

  render.renderSummary = renderSummary;
  window.renderSummary = renderSummary;
})();
