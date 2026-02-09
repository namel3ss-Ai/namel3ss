(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const diagnostics = root.diagnostics || (root.diagnostics = {});

  function diagnosticsPages(manifest) {
    const pages = manifest && Array.isArray(manifest.pages) ? manifest.pages : [];
    return pages
      .map((page) => {
        const blocks = Array.isArray(page && page.diagnostics_blocks) ? page.diagnostics_blocks : [];
        return {
          name: page && page.name ? String(page.name) : "Page",
          slug: page && page.slug ? String(page.slug) : "",
          diagnosticsPage: Boolean(page && page.diagnostics),
          blocks,
        };
      })
      .filter((entry) => entry.diagnosticsPage || entry.blocks.length > 0);
  }

  function renderDiagnostics() {
    const host = document.getElementById("diagnostics");
    if (!host) return;
    host.innerHTML = "";
    const diagnosticsPayload = state && typeof state.getCachedDiagnostics === "function" ? state.getCachedDiagnostics() : null;
    const renderedUnified = renderUnifiedDiagnostics(host, diagnosticsPayload);
    if (renderedUnified) return;
    const manifest = state && typeof state.getCachedManifest === "function" ? state.getCachedManifest() : null;
    const entries = diagnosticsPages(manifest);
    if (!entries.length) {
      const empty = document.createElement("div");
      empty.className = "data-empty";
      empty.textContent = "No diagnostics pages or blocks declared.";
      host.appendChild(empty);
      return;
    }
    entries.forEach((entry) => {
      const card = document.createElement("section");
      card.className = "data-section";
      const title = document.createElement("div");
      title.className = "data-title";
      title.textContent = entry.name;
      card.appendChild(title);

      const list = document.createElement("div");
      list.className = "list";
      const pageType = document.createElement("div");
      pageType.className = "list-item";
      pageType.textContent = entry.diagnosticsPage ? "Type: diagnostics page" : "Type: product page with diagnostics block";
      list.appendChild(pageType);
      const slug = document.createElement("div");
      slug.className = "list-item";
      slug.textContent = `Slug: ${entry.slug || "-"}`;
      list.appendChild(slug);
      const count = document.createElement("div");
      count.className = "list-item";
      count.textContent = `Diagnostics blocks: ${entry.blocks.length}`;
      list.appendChild(count);
      card.appendChild(list);

      if (entry.blocks.length) {
        const blockList = document.createElement("div");
        blockList.className = "list";
        entry.blocks.forEach((block) => {
          const row = document.createElement("div");
          row.className = "list-item";
          const kind = block && block.type ? String(block.type) : "element";
          const label = block && block.label ? ` (${block.label})` : "";
          row.textContent = `${kind}${label}`;
          blockList.appendChild(row);
        });
        card.appendChild(blockList);
      }
      host.appendChild(card);
    });
  }

  function renderUnifiedDiagnostics(host, payload) {
    if (!payload || typeof payload !== "object") return false;
    const diagnosticsList = Array.isArray(payload.diagnostics) ? payload.diagnostics : [];
    const hasRunDiff = payload.run_diff && typeof payload.run_diff === "object";
    const hasRepro = payload.repro_bundle && typeof payload.repro_bundle === "object";
    const hasHistory = Array.isArray(payload.run_history) && payload.run_history.length > 0;
    if (!diagnosticsList.length && !hasRunDiff && !hasRepro && !hasHistory) {
      return false;
    }

    const workspaceId = textValue(payload.workspace_id);
    const sessionId = textValue(payload.session_id);
    if (workspaceId || sessionId) {
      const meta = document.createElement("section");
      meta.className = "data-section";
      const title = document.createElement("div");
      title.className = "data-title";
      title.textContent = "Workspace and Session";
      meta.appendChild(title);
      const list = document.createElement("div");
      list.className = "list";
      if (workspaceId) list.appendChild(listItem(`workspace_id: ${workspaceId}`));
      if (sessionId) list.appendChild(listItem(`session_id: ${sessionId}`));
      meta.appendChild(list);
      host.appendChild(meta);
    }

    const summary = payload.summary && typeof payload.summary === "object" ? payload.summary : {};
    if (Object.keys(summary).length) {
      const section = document.createElement("section");
      section.className = "data-section";
      const title = document.createElement("div");
      title.className = "data-title";
      title.textContent = "Diagnostics Summary";
      section.appendChild(title);
      const list = document.createElement("div");
      list.className = "list";
      ["error", "warn", "info"].forEach((key) => {
        const value = Number(summary[key]);
        if (!Number.isFinite(value)) return;
        list.appendChild(listItem(`${key}: ${Math.max(0, Math.trunc(value))}`));
      });
      section.appendChild(list);
      host.appendChild(section);
    }

    const diagnosticsElement = { type: "diagnostics_panel", entries: diagnosticsList };
    if (typeof window.renderDiagnosticsElement === "function") {
      host.appendChild(window.renderDiagnosticsElement(diagnosticsElement));
    }

    if (hasRunDiff && typeof window.renderRunDiffElement === "function") {
      host.appendChild(window.renderRunDiffElement(payload.run_diff));
    }

    if (hasRepro) {
      host.appendChild(renderReproSection(payload.repro_bundle));
    }
    if (hasHistory) {
      host.appendChild(renderHistorySection(payload.run_history));
    }
    return true;
  }

  function renderReproSection(reproBundle) {
    const section = document.createElement("section");
    section.className = "data-section";
    const title = document.createElement("div");
    title.className = "data-title";
    title.textContent = "Share this run";
    section.appendChild(title);

    const pathValue = textValue(reproBundle.repro_path) || "studio/repro/latest.json";
    const runId = textValue(reproBundle.run_id) || "latest";
    const hint = document.createElement("div");
    hint.className = "data-empty";
    hint.textContent = `Read-only repro: .namel3ss/${pathValue}`;
    section.appendChild(hint);

    const actions = document.createElement("div");
    actions.className = "json-actions";
    const copyJson = document.createElement("button");
    copyJson.type = "button";
    copyJson.className = "btn ghost";
    copyJson.textContent = "Copy repro JSON";
    copyJson.onclick = () => copyText(JSON.stringify(reproBundle, null, 2));
    actions.appendChild(copyJson);

    const copyReplay = document.createElement("button");
    copyReplay.type = "button";
    copyReplay.className = "btn ghost";
    copyReplay.textContent = "Copy replay command";
    copyReplay.onclick = () => copyText(`n3 replay --artifact .namel3ss/audit/${runId}/run_artifact.json`);
    actions.appendChild(copyReplay);
    section.appendChild(actions);
    return section;
  }

  function renderHistorySection(history) {
    const section = document.createElement("section");
    section.className = "data-section";
    const title = document.createElement("div");
    title.className = "data-title";
    title.textContent = "Run History";
    section.appendChild(title);
    const list = document.createElement("div");
    list.className = "list";
    history.forEach((entry) => {
      const value = historyRow(entry);
      if (!value) return;
      list.appendChild(listItem(value));
    });
    if (!list.children.length) {
      list.appendChild(listItem("No runs recorded."));
    }
    section.appendChild(list);
    return section;
  }

  function historyRow(entry) {
    if (typeof entry === "string" && entry.trim()) return entry.trim();
    if (!entry || typeof entry !== "object") return "";
    const runId = textValue(entry.run_id);
    const integrityHash = textValue(entry.integrity_hash);
    if (!runId) return "";
    return integrityHash ? `${runId} (${integrityHash.slice(0, 12)})` : runId;
  }

  function listItem(text) {
    const row = document.createElement("div");
    row.className = "list-item";
    row.textContent = text;
    return row;
  }

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function copyText(text) {
    const value = typeof text === "string" ? text : JSON.stringify(text, null, 2);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value);
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "absolute";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  diagnostics.renderDiagnostics = renderDiagnostics;
  window.renderDiagnostics = renderDiagnostics;
})();
