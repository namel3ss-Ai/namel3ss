(() => {
  const config = window.N3RuntimeConfig || {};
  const mode = config.mode === "dev" ? "dev" : "preview";
  const pollInterval = Number.isFinite(config.pollIntervalMs) ? config.pollIntervalMs : 900;

  const uiContainer = document.getElementById("ui");
  const overlay = document.getElementById("devOverlay");
  const overlayTitle = document.getElementById("devOverlayTitle");
  const overlaySummary = document.getElementById("devOverlaySummary");
  const overlaySections = document.getElementById("devOverlaySections");
  const overlayToggle = document.getElementById("devOverlayToggle");
  const overlayDetails = document.getElementById("devOverlayDetails");
  const overlayCard = overlay ? overlay.querySelector(".overlay-card") : null;
  const statusLabel = document.getElementById("runtimeStatus");
  const appLabel = document.getElementById("appLabel");
  const LAYOUT_SLOTS = ["header", "sidebar_left", "main", "drawer_right", "footer"];

  const state = {
    manifest: null,
    revision: "",
  };
  const rendererRegistryReady = resolveRendererRegistryReady();

  function resolveRendererRegistryReady() {
    const registry = window.N3RendererRegistry;
    if (!registry || typeof registry !== "object") return Promise.resolve();
    if (!registry.ready || typeof registry.ready.then !== "function") {
      return Promise.reject(new Error("Renderer registry readiness promise is missing."));
    }
    return registry.ready;
  }

  function showEmpty(container, message) {
    if (!container) return;
    container.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = message;
    container.appendChild(empty);
  }

  function showError(container, detail) {
    if (!container) return;
    container.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty-state status-error";
    const summary = document.createElement("div");
    summary.textContent = extractSummary(detail);
    empty.appendChild(summary);
    container.appendChild(empty);
  }

  function extractSummary(payload) {
    if (!payload) return "Unable to load UI.";
    if (typeof payload === "string") return payload;
    if (payload.overlay && payload.overlay.summary) return payload.overlay.summary;
    if (payload.error) return payload.error;
    if (payload.message) return payload.message;
    return "Unable to load UI.";
  }

  function updateAppLabel(manifest) {
    if (!appLabel || !manifest || !manifest.pages) return;
    for (const page of manifest.pages) {
      const queue = pageRootElements(page);
      while (queue.length) {
        const element = queue.shift();
        if (!element) continue;
        if (element.type === "title" && element.value) {
          appLabel.textContent = element.value;
          return;
        }
        if (Array.isArray(element.children)) {
          queue.push(...element.children);
        }
      }
    }
  }

  function pageRootElements(page) {
    if (!page || typeof page !== "object") return [];
    if (page.layout && typeof page.layout === "object") {
      const elements = [];
      LAYOUT_SLOTS.forEach((slot) => {
        const slotElements = page.layout[slot];
        if (Array.isArray(slotElements)) {
          elements.push(...slotElements);
        }
      });
      return elements;
    }
    return Array.isArray(page.elements) ? [...page.elements] : [];
  }

  function applyThemeFromManifest(manifest) {
    const theme = (manifest && manifest.theme) || {};
    if (typeof applyThemeBundle === "function") {
      applyThemeBundle(theme);
      return;
    }
    const setting = theme.current || theme.setting || "light";
    if (typeof applyTheme === "function") applyTheme(setting);
    if (typeof applyThemeTokens === "function") applyThemeTokens(theme.tokens || {}, setting);
  }

  function applyManifest(manifest) {
    if (!manifest) return;
    state.manifest = manifest;
    if (typeof renderUI === "function") renderUI(manifest);
    updateAppLabel(manifest);
    applyThemeFromManifest(manifest);
  }

  function renderOverlay(payload) {
    if (!overlay || !payload) return;
    overlay.classList.remove("hidden");
    if (overlayTitle) overlayTitle.textContent = payload.title || "something went wrong";
    if (overlaySummary) overlaySummary.textContent = payload.summary || "";
    if (overlaySections) overlaySections.innerHTML = "";
    const sections = Array.isArray(payload.sections) ? payload.sections : [];
    sections.forEach((section) => {
      if (!overlaySections) return;
      const block = document.createElement("div");
      const title = document.createElement("div");
      title.className = "overlay-section-title";
      title.textContent = section.title || "";
      block.appendChild(title);
      if (Array.isArray(section.items)) {
        const list = document.createElement("ul");
        list.className = "overlay-section-list";
        section.items.forEach((item) => {
          const li = document.createElement("li");
          li.textContent = item;
          list.appendChild(li);
        });
        block.appendChild(list);
      } else if (section.body) {
        const body = document.createElement("div");
        body.className = "overlay-section-body";
        body.textContent = section.body;
        block.appendChild(body);
      }
      overlaySections.appendChild(block);
    });
    const details = payload.details;
    if (overlayToggle && overlayDetails) {
      if (typeof details === "string" && details) {
        overlayToggle.classList.remove("hidden");
        overlayToggle.setAttribute("aria-expanded", "false");
        overlayDetails.classList.add("hidden");
        overlayDetails.textContent = details;
        overlayToggle.onclick = () => toggleDetails();
      } else {
        overlayToggle.classList.add("hidden");
        overlayDetails.classList.add("hidden");
        overlayDetails.textContent = "";
      }
    }
    if (overlayCard && overlayCard.focus) overlayCard.focus();
  }

  function toggleDetails() {
    if (!overlayToggle || !overlayDetails) return;
    const isHidden = overlayDetails.classList.contains("hidden");
    overlayDetails.classList.toggle("hidden", !isHidden);
    overlayToggle.setAttribute("aria-expanded", isHidden ? "true" : "false");
  }

  function clearOverlay() {
    if (!overlay) return;
    overlay.classList.add("hidden");
    if (overlayToggle) overlayToggle.classList.add("hidden");
    if (overlayDetails) {
      overlayDetails.classList.add("hidden");
      overlayDetails.textContent = "";
    }
  }

  function setStatus(text) {
    if (!statusLabel) return;
    statusLabel.textContent = text;
  }

  function runtimeError(category, message, hint, origin, stableCode) {
    return {
      category: category,
      message: message,
      hint: hint,
      origin: origin,
      stable_code: stableCode,
    };
  }

  function networkRuntimeError(path) {
    return runtimeError(
      "server_unavailable",
      "Runtime server is unavailable.",
      `Start the runtime server and retry ${path}.`,
      "network",
      "runtime.server_unavailable"
    );
  }

  function errorWithRuntime(err, runtimeErr, status, payload) {
    const message = (runtimeErr && runtimeErr.message) || (err && err.message) || "Request failed";
    const wrapped = new Error(message);
    wrapped.runtime_error = runtimeErr;
    if (Number.isInteger(status)) wrapped.status = status;
    if (payload && typeof payload === "object") wrapped.payload = payload;
    return wrapped;
  }

  async function fetchJson(path, options) {
    let response;
    try {
      response = await fetch(path, options);
    } catch (err) {
      throw errorWithRuntime(err, networkRuntimeError(path));
    }
    let payload = null;
    try {
      payload = await response.json();
    } catch (_err) {
      payload = null;
    }
    if (payload && typeof payload === "object") {
      return payload;
    }
    if (response.ok) return {};
    const runtimeErr = runtimeError(
      response.status === 401 || response.status === 403 ? "auth_invalid" : "runtime_internal",
      `Request failed with status ${response.status}.`,
      "Check server logs and retry the request.",
      "runtime",
      `runtime.http_${response.status}`
    );
    throw errorWithRuntime(null, runtimeErr, response.status, payload);
  }

  function handleError(payload) {
    if (mode === "dev") {
      const overlayPayload = payload && payload.overlay ? payload.overlay : buildFallbackOverlay(payload);
      renderOverlay(overlayPayload);
      setStatus("Needs attention");
      if (!state.manifest && typeof renderUIError === "function") {
        renderUIError(extractSummary(payload));
      }
      return;
    }
    setStatus("Unable to load preview");
    if (!state.manifest && uiContainer) {
      showError(uiContainer, payload);
    }
  }

  function buildFallbackOverlay(payload) {
    const summary = extractSummary(payload);
    return {
      title: "something went wrong",
      summary: summary,
      sections: summary ? [{ title: "what happened", body: summary }] : [],
    };
  }

  async function refreshUI() {
    try {
      const payload = await fetchJson("/api/ui");
      if (payload && payload.ok === false) {
        handleError(payload);
        return;
      }
      clearOverlay();
      setStatus("Up to date");
      applyManifest(payload);
    } catch (err) {
      const runtimeErr = err && err.runtime_error ? err.runtime_error : null;
      handleError(runtimeErr || (err && err.message ? err.message : "Unable to load UI."));
    }
  }

  async function pollStatus() {
    try {
      const status = await fetchJson("/api/dev/status");
      if (!status || typeof status.ok !== "boolean") return;
      if (!status.ok) {
        handleError(status.error || status);
        return;
      }
      clearOverlay();
      setStatus("Up to date");
      if (status.revision && status.revision !== state.revision) {
        state.revision = status.revision;
        refreshUI();
      }
    } catch (_err) {
      setStatus("Disconnected");
    }
  }

  async function executeAction(actionId, payload) {
    try {
      const response = await fetchJson("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: actionId, payload: payload || {} }),
      });
      if (response && response.ui) {
        applyManifest(response.ui);
      }
      if (response && response.ok === false) {
        handleError(response);
      }
      return response;
    } catch (err) {
      const runtimeErr = err && err.runtime_error ? err.runtime_error : null;
      handleError(runtimeErr || (err && err.message ? err.message : "Action failed."));
      return { ok: false, error: "Action failed." };
    }
  }

  window.showEmpty = showEmpty;
  window.showError = showError;
  window.executeAction = executeAction;

  rendererRegistryReady
    .then(() => {
      refreshUI();
      if (mode === "dev") {
        setStatus("Watching for changes");
        setInterval(pollStatus, pollInterval);
      }
    })
    .catch((err) => {
      const stableCode = err && err.error_code ? String(err.error_code) : "N3E_RENDERER_REGISTRY_INVALID";
      handleError({ message: `${stableCode}: renderer registry failed to load.` });
    });
})();
