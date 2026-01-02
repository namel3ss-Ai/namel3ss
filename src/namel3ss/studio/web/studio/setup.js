(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const setup = root.setup || (root.setup = {});
  const secretsApi = root.secrets || {};

  let cachedPayload = null;
  let loading = false;
  let loadingPromise = null;
  let acknowledgedMissing = false;
  let lastMissingKey = "";
  const PROVIDER_LABELS = {
    openai: "OpenAI",
    anthropic: "Anthropic",
    gemini: "Gemini",
    mistral: "Mistral",
  };

  function looksLikeSecretValue(value) {
    if (!value) return false;
    const text = String(value).trim();
    if (!text) return false;
    if (text.startsWith("sk-")) return true;
    if (text.length >= 40 && !/[_A-Z]/.test(text)) return true;
    return false;
  }

  function sanitizeSecretName(name) {
    const text = String(name || "").trim();
    if (!text) return "UNKNOWN_SECRET";
    if (looksLikeSecretValue(text)) return "[redacted]";
    return text;
  }

  function expandPlaceholders(provider, text) {
    if (typeof secretsApi.expandPlaceholders === "function") {
      return secretsApi.expandPlaceholders(provider, text);
    }
    return text;
  }

  function getAiSecretLabel(name) {
    if (typeof secretsApi.providerForKey !== "function") return null;
    const provider = secretsApi.providerForKey(name);
    if (!provider) return null;
    return PROVIDER_LABELS[provider] || provider.toUpperCase();
  }

  function formatSecretName(rawName) {
    const name = String(rawName || "").trim();
    const safeName = sanitizeSecretName(name);
    if (typeof secretsApi.providerForKey !== "function" || typeof secretsApi.listProviderKeys !== "function") {
      return safeName;
    }
    const provider = secretsApi.providerForKey(name);
    if (!provider) return safeName;
    const aliases = secretsApi.listProviderKeys(provider).map((alias) => sanitizeSecretName(alias));
    const filtered = aliases.filter((alias) => alias && alias !== safeName);
    if (!filtered.length) return safeName;
    return `${safeName} (or ${filtered.join(", ")})`;
  }

  function normalizeSource(source) {
    const value = String(source || "").trim();
    if (!value) return "missing";
    return value;
  }

  function collectMissingSecretNames(secrets) {
    return (secrets || [])
      .filter((item) => item && item.available === false)
      .map((item) => String(item.name || "").trim())
      .filter((name) => name);
  }

  function missingSecrets(secrets) {
    const missing = (secrets || []).filter((item) => item && item.available === false);
    const names = missing.map((item) => sanitizeSecretName(item.name));
    const key = names.join("|");
    if (key !== lastMissingKey) {
      acknowledgedMissing = false;
      lastMissingKey = key;
    }
    return names;
  }

  function updateBanner(missing) {
    const banner = document.getElementById("setupBanner");
    if (!banner) return;
    if (!missing.length) {
      banner.classList.add("hidden");
      banner.textContent = "";
      return;
    }
    banner.classList.remove("hidden");
    banner.textContent = `Missing secrets: ${missing.join(", ")}`;
  }

  function normalizeProvider(provider) {
    return String(provider || "").trim().toLowerCase();
  }

  function getSummaryPayload() {
    if (root.state && typeof root.state.getCachedSummary === "function") {
      return root.state.getCachedSummary();
    }
    return null;
  }

  function getProvidersFromSummary(summary) {
    const providers = summary && Array.isArray(summary.ai_providers) ? summary.ai_providers : [];
    return providers.map(normalizeProvider).filter(Boolean);
  }

  function hasAi(summary, secrets) {
    const providers = getProvidersFromSummary(summary);
    const count = summary && summary.counts ? Number(summary.counts.ais || 0) : 0;
    if (providers.length || count > 0) return true;
    return (secrets || []).some((item) => item && getAiSecretLabel(item.name));
  }

  function selectAiBadgeState(summary, secrets) {
    const providers = getProvidersFromSummary(summary);
    const aiSecrets = (secrets || []).filter((item) => item && getAiSecretLabel(item.name));
    const hasRealProvider =
      providers.some((provider) => provider && provider !== "mock"
        && typeof secretsApi.getProviderKeys === "function"
        && secretsApi.getProviderKeys(provider))
      || aiSecrets.length > 0;
    const providerKeys = providers
      .map((provider) => {
        if (typeof secretsApi.getProviderKeys !== "function") return null;
        const keys = secretsApi.getProviderKeys(provider);
        return keys ? keys.canonical : null;
      })
      .filter((name) => name);
    const relevantSecrets = providerKeys.length
      ? aiSecrets.filter((item) => providerKeys.includes(item.name))
      : aiSecrets;
    const missing = relevantSecrets.filter((item) => item && item.available === false);
    const available = relevantSecrets.filter((item) => item && item.available === true);
    if (!hasRealProvider) {
      return { status: "mock", label: "AI: Mock", showSetup: false };
    }
    if (missing.length) {
      return { status: "missing", label: "AI: Mock (missing keys)", showSetup: true };
    }
    if (available.length) {
      const label = getAiSecretLabel(available[0].name) || "Ready";
      return { status: "ready", label: `AI: ${label}`, showSetup: false };
    }
    return { status: "mock", label: "AI: Mock", showSetup: true };
  }

  function updateAiBadge(summaryPayload) {
    const badge = document.getElementById("aiModeBadge");
    const label = document.getElementById("aiModeBadgeText");
    const button = document.getElementById("aiModeBadgeSetup");
    if (!badge || !label) return;
    const summary = summaryPayload || getSummaryPayload();
    const secrets = cachedPayload && Array.isArray(cachedPayload.secrets) ? cachedPayload.secrets : [];
    if (!hasAi(summary, secrets)) {
      badge.classList.add("hidden");
      return;
    }
    const state = selectAiBadgeState(summary, secrets);
    badge.classList.remove("hidden");
    badge.dataset.status = state.status;
    label.textContent = state.label;
    if (button) {
      button.classList.toggle("hidden", !state.showSetup);
      button.onclick = state.showSetup ? openSetupTab : null;
    }
  }

  function buildSecretsTable(secrets, fallbackTarget) {
    const table = document.createElement("table");
    table.className = "ui-table setup-table";
    const head = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Name", "Status", "Source", "Target"].forEach((label) => {
      const th = document.createElement("th");
      th.textContent = label;
      headerRow.appendChild(th);
    });
    head.appendChild(headerRow);
    table.appendChild(head);
    const body = document.createElement("tbody");
    (secrets || []).forEach((secret) => {
      const row = document.createElement("tr");
      const name = document.createElement("td");
      name.textContent = formatSecretName(secret && secret.name);
      const status = document.createElement("td");
      const available = secret && secret.available === true;
      status.textContent = available ? "available ✅" : "missing ❌";
      const source = document.createElement("td");
      source.textContent = normalizeSource(secret && secret.source);
      const target = document.createElement("td");
      target.textContent = String((secret && secret.target) || fallbackTarget || "local");
      row.appendChild(name);
      row.appendChild(status);
      row.appendChild(source);
      row.appendChild(target);
      body.appendChild(row);
    });
    table.appendChild(body);
    return table;
  }

  function buildFixSnippet(missingNames) {
    const wrapper = document.createElement("div");
    wrapper.className = "panel-body";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "How to fix";
    const code = document.createElement("div");
    code.className = "code-block";
    const target = missingNames && missingNames.length ? missingNames[0] : "SOME_API_KEY";
    const safeTarget = sanitizeSecretName(target);
    const provider = typeof secretsApi.providerForKey === "function" ? secretsApi.providerForKey(target) : null;
    let setLine = `set ${safeTarget}="..."`;
    if (provider && typeof secretsApi.expandPlaceholders === "function") {
      setLine = expandPlaceholders(
        provider,
        'set <CANONICAL_KEY>="..." (preferred) or <ALIAS_KEY>="..."'
      );
      if (typeof secretsApi.listProviderKeys === "function") {
        const keys = secretsApi.listProviderKeys(provider);
        const extras = keys.length > 2
          ? keys.slice(2).map((alias) => `${sanitizeSecretName(alias)}="..."`)
          : [];
        if (extras.length) {
          setLine = `${setLine}, or ${extras.join(", ")}`;
        }
      }
    }
    code.textContent = `cp .env.example .env\n${setLine}\nn3 secrets status --json`;
    wrapper.appendChild(title);
    wrapper.appendChild(code);
    return wrapper;
  }

  function hasProviderErrors() {
    const traces = root.state && typeof root.state.getCachedTraces === "function"
      ? root.state.getCachedTraces()
      : [];
    return (traces || []).some((trace) => {
      const events = trace && Array.isArray(trace.canonical_events) ? trace.canonical_events : [];
      return events.some((event) => event && event.type === "ai_provider_error");
    });
  }

  function openTracesTab() {
    if (root.dock && typeof root.dock.setActiveTab === "function") {
      root.dock.setActiveTab("traces");
    }
  }

  function buildProviderErrorBanner() {
    const banner = document.createElement("div");
    banner.className = "status-banner warning";
    const text = document.createElement("div");
    text.textContent = "Provider error detected. See Traces.";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn ghost";
    button.textContent = "Open Traces";
    button.onclick = openTracesTab;
    banner.appendChild(text);
    banner.appendChild(button);
    return banner;
  }

  function renderSetup(payload) {
    const panel = document.getElementById("setup");
    if (!panel) return;
    panel.innerHTML = "";
    if (!payload || payload.ok === false) {
      const message = payload && payload.error ? payload.error : "Unable to load secrets.";
      dom.showError(panel, message);
      updateBanner([]);
      return;
    }
    const secrets = Array.isArray(payload.secrets) ? payload.secrets : [];
    const missing = missingSecrets(secrets);
    const missingNames = collectMissingSecretNames(secrets);

    if (!secrets.length) {
      panel.appendChild(dom.buildEmpty("No secrets required for this app ✅"));
      updateBanner([]);
      updateAiBadge(payload);
      return;
    }

    const wrapper = document.createElement("div");
    wrapper.className = "setup-panel";

    const section = document.createElement("div");
    section.className = "panel-section";
    const sectionTitle = document.createElement("div");
    sectionTitle.className = "panel-section-title";
    sectionTitle.textContent = "Required secrets";
    section.appendChild(sectionTitle);
    wrapper.appendChild(section);

    wrapper.appendChild(buildSecretsTable(secrets, payload.target));

    if (missingNames.length) {
      wrapper.appendChild(buildFixSnippet(missingNames));
    } else if (hasProviderErrors()) {
      wrapper.appendChild(buildProviderErrorBanner());
    }

    panel.appendChild(wrapper);
    updateBanner(missing);
    updateAiBadge(payload);
  }

  async function refreshSetup() {
    const panel = document.getElementById("setup");
    if (loadingPromise) return loadingPromise;
    loading = true;
    if (panel) dom.showEmpty(panel, "Loading secrets...");
    loadingPromise = (async () => {
      try {
        const payload = await net.fetchJson("/api/secrets");
        cachedPayload = payload;
        renderSetup(payload);
      } catch (err) {
        const detail = err && err.message ? err.message : "Unable to load secrets.";
        if (panel) dom.showError(panel, detail);
        updateBanner([]);
      } finally {
        loading = false;
        loadingPromise = null;
      }
    })();
    return loadingPromise;
  }

  function openSetupTab() {
    if (root.dock && typeof root.dock.setActiveTab === "function") {
      root.dock.setActiveTab("setup");
    }
  }

  async function confirmProceed() {
    if (!cachedPayload && !loading) {
      await refreshSetup();
    }
    const secrets = cachedPayload && Array.isArray(cachedPayload.secrets) ? cachedPayload.secrets : [];
    const missing = missingSecrets(secrets);
    if (!missing.length || acknowledgedMissing) {
      return true;
    }
    const modal = document.getElementById("secretsModal");
    const body = document.getElementById("secretsModalBody");
    const close = document.getElementById("secretsModalClose");
    const setupButton = document.getElementById("secretsModalSetup");
    const continueButton = document.getElementById("secretsModalContinue");
    if (!modal || !body || !close || !setupButton || !continueButton) {
      return true;
    }
    body.textContent = `This action may require secrets that are missing: ${missing.join(", ")}`;
    modal.classList.remove("hidden");
    return new Promise((resolve) => {
      const cleanup = (proceed) => {
        modal.classList.add("hidden");
        close.removeEventListener("click", onClose);
        setupButton.removeEventListener("click", onSetup);
        continueButton.removeEventListener("click", onContinue);
        resolve(proceed);
      };
      const onClose = () => cleanup(false);
      const onSetup = () => {
        cleanup(false);
        openSetupTab();
      };
      const onContinue = () => {
        acknowledgedMissing = true;
        cleanup(true);
      };
      close.addEventListener("click", onClose);
      setupButton.addEventListener("click", onSetup);
      continueButton.addEventListener("click", onContinue);
    });
  }

  function getMissingSecrets() {
    const secrets = cachedPayload && Array.isArray(cachedPayload.secrets) ? cachedPayload.secrets : [];
    return missingSecrets(secrets);
  }

  setup.renderSetup = renderSetup;
  setup.refreshSetup = refreshSetup;
  setup.getMissingSecrets = getMissingSecrets;
  setup.confirmProceed = confirmProceed;
  setup.updateAiBadge = updateAiBadge;
})();
