let cachedDiscover = { results: [] };

function setupDiscoverPanel() {
  const phraseInput = document.getElementById("discoverPhrase");
  const capabilitySelect = document.getElementById("discoverCapability");
  const riskSelect = document.getElementById("discoverRisk");
  const searchButton = document.getElementById("discoverSearch");
  const copyButton = document.getElementById("discoverCopy");
  if (!phraseInput || !searchButton) return;

  const runSearch = async () => {
    const phrase = phraseInput.value.trim();
    if (!phrase) {
      showToast("Intent phrase required.");
      return;
    }
    const capability = capabilitySelect ? capabilitySelect.value || null : null;
    const risk = riskSelect ? riskSelect.value || null : null;
    const payload = { phrase, capability: capability || null, risk: risk || null };
    try {
      const resp = await postJson("/api/discover", payload);
      if (!resp.ok) {
        showToast(resp.error || "Discover failed.");
        return;
      }
      cachedDiscover = resp;
      renderDiscoverResults(resp.results || []);
    } catch (err) {
      showToast("Discover failed.");
    }
  };

  searchButton.onclick = runSearch;
  phraseInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });
  if (copyButton) {
    copyButton.onclick = () => copyText(cachedDiscover);
  }
}

function renderDiscoverResults(results) {
  const container = document.getElementById("discoverResults");
  if (!container) return;
  container.innerHTML = "";
  if (!results || !results.length) {
    showEmpty(container, "No matching packs.");
    return;
  }
  results.forEach((result) => {
    const card = document.createElement("div");
    card.className = "panel-body";
    card.style.marginBottom = "12px";
    const header = document.createElement("div");
    header.className = "panel-header";
    const title = document.createElement("div");
    title.className = "section-title";
    title.textContent = `${result.pack_name} (${result.pack_id}@${result.pack_version})`;
    const badges = document.createElement("div");
    badges.className = "panel-actions";
    badges.innerHTML = `<span class="badge">${result.trusted ? "verified" : "unverified"}</span>
      <span class="badge">risk: ${result.risk}</span>`;
    header.appendChild(title);
    header.appendChild(badges);

    const body = document.createElement("div");
    body.style.marginTop = "8px";
    const tools = Array.isArray(result.tools) ? result.tools : [];
    const tokens = Array.isArray(result.matched_tokens) ? result.matched_tokens : [];
    const blocked = result.blocked_by_policy ? "blocked by policy" : "";
    body.innerHTML = `
      <div><strong>Tools:</strong> ${tools.join(", ") || "n/a"}</div>
      <div><strong>Matched:</strong> ${tokens.join(", ") || "n/a"}</div>
      <div><strong>Status:</strong> ${blocked || "ok"}</div>
    `;
    if (result.blocked_reasons && result.blocked_reasons.length) {
      const policy = document.createElement("div");
      policy.innerHTML = `<strong>Policy:</strong> ${result.blocked_reasons.join("; ")}`;
      body.appendChild(policy);
    }

    const actions = document.createElement("div");
    actions.className = "panel-actions";
    actions.style.marginTop = "10px";
    const install = document.createElement("button");
    install.className = "btn secondary small";
    install.textContent = "Install";
    install.onclick = () => installPack(result.pack_id, result.pack_version);
    const verify = document.createElement("button");
    verify.className = "btn ghost small";
    verify.textContent = "Verify";
    verify.onclick = () => verifyPack(result.pack_id);
    const enable = document.createElement("button");
    enable.className = "btn ghost small";
    enable.textContent = "Enable";
    enable.onclick = () => enablePack(result.pack_id);
    actions.appendChild(install);
    actions.appendChild(verify);
    actions.appendChild(enable);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(actions);
    container.appendChild(card);
  });
}

async function postJson(path, payload) {
  const resp = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  return resp.json();
}

async function installPack(packId, packVersion) {
  try {
    const resp = await postJson("/api/packs/install", { pack_id: packId, pack_version: packVersion });
    if (!resp.ok) {
      showToast(resp.error || "Install failed.");
      return;
    }
    showToast("Pack installed.");
    refreshAll();
  } catch (err) {
    showToast("Install failed.");
  }
}

async function verifyPack(packId) {
  try {
    const resp = await postJson("/api/packs/verify", { pack_id: packId });
    if (!resp.ok) {
      showToast(resp.error || "Verify failed.");
      return;
    }
    showToast("Pack verified.");
    refreshAll();
  } catch (err) {
    showToast("Verify failed.");
  }
}

async function enablePack(packId) {
  try {
    const resp = await postJson("/api/packs/enable", { pack_id: packId });
    if (!resp.ok) {
      showToast(resp.error || "Enable failed.");
      return;
    }
    showToast("Pack enabled.");
    refreshAll();
  } catch (err) {
    showToast("Enable failed.");
  }
}

setupDiscoverPanel();
