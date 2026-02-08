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

  diagnostics.renderDiagnostics = renderDiagnostics;
  window.renderDiagnostics = renderDiagnostics;
})();
