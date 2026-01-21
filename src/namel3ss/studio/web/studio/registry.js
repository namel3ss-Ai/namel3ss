(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const registry = root.registry || (root.registry = {});

  function formatText(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "string") return value;
    try {
      return JSON.stringify(value, null, 2);
    } catch (err) {
      return String(value);
    }
  }

  function formatCapabilities(capabilities) {
    if (!capabilities || typeof capabilities !== "object") return "none";
    const fs = capabilities.filesystem || "none";
    const net = capabilities.network || "none";
    const env = capabilities.env || "none";
    const sub = capabilities.subprocess || "none";
    const secrets = Array.isArray(capabilities.secrets) ? capabilities.secrets.length : 0;
    return `filesystem ${fs}, network ${net}, env ${env}, subprocess ${sub}, secrets ${secrets}`;
  }

  function buildBadge(text, kind) {
    const badge = document.createElement("span");
    badge.className = `registry-badge ${kind || ""}`.trim();
    badge.textContent = text;
    return badge;
  }

  function buildPackCard(pack) {
    const card = document.createElement("div");
    card.className = "list-item registry-pack";

    const header = document.createElement("div");
    header.className = "registry-pack-header";

    const titleWrap = document.createElement("div");
    const name = document.createElement("div");
    name.className = "registry-pack-name";
    name.textContent = pack.pack_name || pack.pack_id || "Pack";
    const id = document.createElement("div");
    id.className = "registry-pack-id";
    id.textContent = pack.pack_id || "unknown.pack";
    titleWrap.appendChild(name);
    titleWrap.appendChild(id);

    const meta = document.createElement("div");
    meta.className = "registry-pack-meta";
    const parts = [];
    if (pack.installed_version) parts.push(`Installed ${pack.installed_version}`);
    if (pack.latest_version) parts.push(`Latest ${pack.latest_version}`);
    meta.textContent = parts.length ? parts.join(" · ") : "Not installed";

    header.appendChild(titleWrap);
    header.appendChild(meta);
    card.appendChild(header);

    const versions = Array.isArray(pack.versions) ? pack.versions : [];
    if (!versions.length) {
      card.appendChild(dom.buildEmpty("No versions available."));
      return card;
    }

    const versionList = document.createElement("div");
    versionList.className = "registry-version-list";
    versions.forEach((entry) => {
      const versionCard = document.createElement("div");
      versionCard.className = "registry-version-card";

      const headerRow = document.createElement("div");
      headerRow.className = "registry-version-header";
      const versionName = document.createElement("div");
      versionName.className = "registry-version-name";
      versionName.textContent = entry.pack_version || "version";
      headerRow.appendChild(versionName);

      const badgeRow = document.createElement("div");
      badgeRow.className = "registry-badges";
      const trust = entry.trust || {};
      const trustStatus = trust.status || "unknown";
      badgeRow.appendChild(buildBadge(`trust ${trustStatus}`, `trust-${trustStatus}`));
      if (entry.risk) {
        badgeRow.appendChild(buildBadge(`risk ${entry.risk}`, `risk-${entry.risk}`));
      }
      const versionInfo = entry.version || {};
      if (versionInfo.status && versionInfo.status !== "not_installed") {
        badgeRow.appendChild(buildBadge(`compatibility ${versionInfo.status}`, "compatibility"));
      }
      headerRow.appendChild(badgeRow);
      versionCard.appendChild(headerRow);

      const summary = document.createElement("div");
      summary.className = "registry-version-summary";
      const caps = formatCapabilities(entry.capabilities);
      summary.textContent = `Capabilities: ${caps}`;
      versionCard.appendChild(summary);

      const signature = entry.signature || {};
      const signatureStatus = signature.status || "unknown";
      const signatureLine = document.createElement("div");
      signatureLine.className = "registry-version-summary";
      const signatureParts = [`Signature: ${signatureStatus}`];
      if (signature.algorithm) signatureParts.push(signature.algorithm);
      if (Array.isArray(entry.verified_by) && entry.verified_by.length) {
        signatureParts.push(`verified by ${entry.verified_by.join(", ")}`);
      }
      signatureLine.textContent = signatureParts.join(" · ");
      versionCard.appendChild(signatureLine);

      const policyReasons = Array.isArray(trust.policy_reasons) ? trust.policy_reasons : [];
      if (policyReasons.length) {
        const policyLine = document.createElement("div");
        policyLine.className = "registry-version-summary";
        policyLine.textContent = `Policy: ${policyReasons.join("; ")}`;
        versionCard.appendChild(policyLine);
      }

      const intent = document.createElement("div");
      intent.className = "registry-intent";
      intent.textContent = formatText(entry.intent_text || "No intent text.");
      versionCard.appendChild(intent);

      versionList.appendChild(versionCard);
    });
    card.appendChild(versionList);
    return card;
  }

  function renderPackList(container, packs, filterText) {
    container.innerHTML = "";
    const list = document.createElement("div");
    list.className = "list registry-list";
    const query = String(filterText || "").trim().toLowerCase();
    const visible = (packs || []).filter((pack) => {
      if (!query) return true;
      const name = String(pack.pack_name || "").toLowerCase();
      const id = String(pack.pack_id || "").toLowerCase();
      return name.includes(query) || id.includes(query);
    });
    if (!visible.length) {
      list.appendChild(dom.buildEmpty("No registry packs matched."));
      container.appendChild(list);
      return;
    }
    visible.forEach((pack) => list.appendChild(buildPackCard(pack)));
    container.appendChild(list);
  }

  async function renderRegistry() {
    const panel = document.getElementById("registry");
    if (!panel) return;
    panel.innerHTML = "";
    const wrapper = document.createElement("div");
    wrapper.className = "registry-panel";

    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Registry";
    const meta = document.createElement("div");
    meta.className = "registry-meta";
    meta.textContent = "Loading registry...";
    header.appendChild(title);
    header.appendChild(meta);

    const filterRow = document.createElement("div");
    filterRow.className = "registry-controls";
    const filterInput = document.createElement("input");
    filterInput.type = "text";
    filterInput.placeholder = "Filter packs...";
    filterInput.setAttribute("aria-label", "Filter registry packs");
    filterRow.appendChild(filterInput);

    const listWrap = document.createElement("div");
    listWrap.className = "registry-list-wrap";

    wrapper.appendChild(header);
    wrapper.appendChild(filterRow);
    wrapper.appendChild(listWrap);
    panel.appendChild(wrapper);

    try {
      const payload = await net.postJson("/api/registry", {});
      if (!payload || payload.ok === false) {
        dom.showError(listWrap, (payload && payload.error) || "Unable to load registry.");
        meta.textContent = "Registry unavailable";
        return;
      }
      const packs = Array.isArray(payload.packs) ? payload.packs : [];
      const sources = Array.isArray(payload.sources) ? payload.sources : [];
      const sourceLabels = sources.map((source) => source.id || source.kind).filter(Boolean);
      meta.textContent = `${packs.length} packs · sources ${sourceLabels.join(", ") || "local"}`;
      renderPackList(listWrap, packs, "");
      filterInput.addEventListener("input", () => {
        renderPackList(listWrap, packs, filterInput.value);
      });
    } catch (err) {
      dom.showError(listWrap, err && err.message ? err.message : "Unable to load registry.");
      meta.textContent = "Registry unavailable";
    }
  }

  registry.renderRegistry = renderRegistry;
  window.renderRegistry = renderRegistry;
})();
