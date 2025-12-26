(() => {
  let cachedPackages = null;

  function setupPackagesPanel() {
    const searchButton = document.getElementById("packagesSearch");
    const input = document.getElementById("packagesQuery");
    const copyButton = document.getElementById("packagesCopy");
    if (searchButton && input) {
      const runSearch = () => searchPackages(input.value.trim());
      searchButton.onclick = runSearch;
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") runSearch();
      });
    }
    if (copyButton) {
      copyButton.onclick = () => copyText(cachedPackages || {});
    }
  }

  async function searchPackages(query) {
    const container = document.getElementById("packagesResults");
    if (!container) return;
    if (!query) {
      showToast("Search query required.");
      return;
    }
    container.innerHTML = "";
    showStatus(container, "Searching index…", "loading");
    try {
      const payload = await fetchJson(`/api/pkg/search?q=${encodeURIComponent(query)}`);
      cachedPackages = payload;
      renderPackageResults(payload);
    } catch (err) {
      showStatus(container, "Package search failed.", "error");
    }
  }

  function renderPackageResults(payload) {
    const container = document.getElementById("packagesResults");
    if (!container) return;
    container.innerHTML = "";
    if (!payload || payload.ok === false) {
      showStatus(container, payload && payload.error ? payload.error : "Search failed.", "error");
      return;
    }
    const results = Array.isArray(payload.results) ? payload.results : [];
    if (!results.length) {
      showEmpty(container, "No matching packages.");
      return;
    }
    results.forEach((result) => {
      const card = document.createElement("div");
      card.className = "list-item";
      const tags = Array.isArray(result.tags) ? result.tags.join(", ") : "";
      const matched = Array.isArray(result.matched_tokens) ? result.matched_tokens.join(", ") : "";
      card.innerHTML = `
        <div class=\"list-title\">${result.name}</div>
        <div class=\"list-meta\">${result.description}</div>
        <div class=\"list-meta\">tier: ${result.trust_tier}${tags ? ` · tags: ${tags}` : ""}</div>
        <div class=\"list-meta\">matched: ${matched || "n/a"}</div>
      `;
      const actions = document.createElement("div");
      actions.className = "panel-actions";
      const copyBtn = document.createElement("button");
      copyBtn.className = "btn ghost small";
      copyBtn.textContent = "Copy install";
      copyBtn.onclick = () => copyText(result.install || `n3 pkg add ${result.source}`);
      const infoBtn = document.createElement("button");
      infoBtn.className = "btn secondary small";
      infoBtn.textContent = "Info";
      infoBtn.onclick = () => loadPackageInfo(result.name, card);
      actions.appendChild(infoBtn);
      actions.appendChild(copyBtn);
      card.appendChild(actions);
      container.appendChild(card);
    });
  }

  async function loadPackageInfo(name, container) {
    try {
      const payload = await fetchJson(`/api/pkg/info?name=${encodeURIComponent(name)}`);
      if (!payload || payload.ok === false) {
        showToast(payload.error || "Package info failed.");
        return;
      }
      const block = createCodeBlock(payload);
      container.appendChild(block);
    } catch (err) {
      showToast("Package info failed.");
    }
  }

  function showStatus(container, message, kind) {
    const banner = document.createElement("div");
    banner.className = `status-banner ${kind || ""}`.trim();
    banner.textContent = message;
    container.appendChild(banner);
  }

  setupPackagesPanel();
})();
