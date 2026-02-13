(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const actionResult = root.actionResult || {};
  const run = root.run || (root.run = {});

  const RUNNING_LABEL = "Running...";
  const SUCCESS_LABEL = "Run complete.";
  let runLabel = "Run";
  let activeController = null;

  const PREFERRED_SEED_FLOWS = ["seed", "seed_data", "seed_demo", "demo_seed", "seed_customers"];
  const PREFERRED_RESET_FLOWS = ["reset", "reset_state", "reset_demo", "reset_dashboard", "clear_state"];

  function getRunButton() {
    return document.getElementById("run");
  }

  function setRunStatus(kind, lines) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.classList.remove("running", "success", "error");
    if (kind) toast.classList.add(kind);
    toast.innerHTML = "";
    if (lines && lines.length) {
      toast.appendChild(dom.buildStatusLines(lines));
      toast.style.display = "block";
    } else {
      toast.style.display = "none";
    }
  }

  function setRunButtonBusy(isBusy) {
    const button = getRunButton();
    if (!button) return;
    const hasAction = !!state.getSeedActionId();
    button.disabled = isBusy || !hasAction;
    button.textContent = isBusy ? RUNNING_LABEL : runLabel;
  }

  function detectSeedAction(manifest) {
    const actions = manifest && manifest.actions ? Object.values(manifest.actions) : [];
    const callFlows = actions.filter((action) => action && action.type === "call_flow");
    if (!callFlows.length) return null;
    for (const name of PREFERRED_SEED_FLOWS) {
      const found = callFlows.find((action) => action.flow === name);
      if (found) return found.id || found.action_id || null;
    }
    const fallback = callFlows[0];
    return fallback ? fallback.id || fallback.action_id || null : null;
  }

  function updateSeedAction(manifest) {
    const button = getRunButton();
    if (!button) return;
    const seedActionId = detectSeedAction(manifest);
    state.setSeedActionId(seedActionId);
    button.classList.remove("hidden");
    setRunButtonBusy(false);
  }

  function detectResetAction(manifest) {
    const actions = manifest && manifest.actions ? Object.values(manifest.actions) : [];
    const callFlows = actions.filter((action) => action && action.type === "call_flow");
    if (!callFlows.length) return null;
    for (const name of PREFERRED_RESET_FLOWS) {
      const found = callFlows.find((action) => action.flow === name);
      if (found) return found.id || found.action_id || null;
    }
    return null;
  }

  function updateResetAction(manifest) {
    const resetActionId = detectResetAction(manifest);
    state.setResetActionId(resetActionId);
  }

  function _isAbortError(err) {
    return err && (err.name === "AbortError" || String(err).toLowerCase().includes("abort"));
  }

  function _safeJsonParse(text) {
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch (_err) {
      return null;
    }
  }

  function _parseSseFrame(frame) {
    const lines = String(frame || "").split("\n");
    let event = "message";
    const dataLines = [];
    for (const line of lines) {
      if (!line) continue;
      if (line.startsWith("event:")) {
        event = line.slice(6).trim() || "message";
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    return { event, data: _safeJsonParse(dataLines.join("\n")) };
  }

  function _withStreamQuery(path) {
    if (typeof path !== "string" || !path) return path;
    return path.includes("?") ? `${path}&stream=true` : `${path}?stream=true`;
  }

  function _threadRoutePath(threadId, routeName, activate) {
    const text = typeof threadId === "string" ? threadId.trim() : "";
    if (!text) return "";
    const encoded = encodeURIComponent(text);
    const actionName = routeName === "save" ? "save" : "load";
    const queryValue = activate === false ? "false" : "true";
    return `/api/chat/threads/${encoded}/${actionName}?activate=${queryValue}`;
  }

  async function _streamChatRoute(path, requestOptions) {
    const options = requestOptions || {};
    const method = typeof options.method === "string" ? options.method.toUpperCase() : "GET";
    const onEvent = typeof options.onEvent === "function" ? options.onEvent : null;
    const body = options.body && typeof options.body === "object" ? options.body : {};
    const fetchOptions = {
      method,
      headers: { Accept: "text/event-stream" },
      signal: options.signal || undefined,
    };
    if (method !== "GET") {
      fetchOptions.headers["Content-Type"] = "application/json";
      fetchOptions.body = JSON.stringify(body);
    }
    const response = await fetch(_withStreamQuery(path), fetchOptions);
    if (!response.ok) {
      const text = await response.text();
      const parsed = _safeJsonParse(text);
      if (parsed && typeof parsed === "object") {
        return parsed;
      }
      return { ok: false, error: text || `Request failed with status ${response.status}` };
    }
    if (!response.body) {
      const text = await response.text();
      let finalPayload = {};
      for (const frame of String(text || "").split("\n\n")) {
        if (!frame.trim()) continue;
        const parsed = _parseSseFrame(frame);
        if (parsed.event === "return" && parsed.data && typeof parsed.data === "object") {
          finalPayload = parsed.data;
        } else if (onEvent) {
          onEvent(parsed);
        }
      }
      return finalPayload;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload = {};
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      let splitAt = buffer.indexOf("\n\n");
      while (splitAt >= 0) {
        const frame = buffer.slice(0, splitAt);
        buffer = buffer.slice(splitAt + 2);
        const parsed = _parseSseFrame(frame);
        if (parsed.event === "return" && parsed.data && typeof parsed.data === "object") {
          finalPayload = parsed.data;
        } else if (onEvent) {
          onEvent(parsed);
        }
        splitAt = buffer.indexOf("\n\n");
      }
    }
    if (buffer.trim()) {
      const parsed = _parseSseFrame(buffer);
      if (parsed.event === "return" && parsed.data && typeof parsed.data === "object") {
        finalPayload = parsed.data;
      } else if (onEvent) {
        onEvent(parsed);
      }
    }
    return finalPayload;
  }

  async function _requestChatRoute(path, requestOptions) {
    const options = requestOptions || {};
    const method = typeof options.method === "string" ? options.method.toUpperCase() : "GET";
    const stream = options.stream === true;
    if (stream) {
      return _streamChatRoute(path, {
        method,
        body: options.body,
        onEvent: options.onEvent,
        signal: options.signal,
      });
    }
    if (!net || typeof net.fetchJson !== "function") {
      return { ok: false, error: "Network client is unavailable." };
    }
    if (method === "GET") {
      return net.fetchJson(path);
    }
    const body = options.body && typeof options.body === "object" ? options.body : {};
    return net.fetchJson(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  async function _refreshAfterChatRoute(options) {
    const opts = options || {};
    if (opts.refreshUI !== false && root.refresh && typeof root.refresh.refreshUI === "function") {
      await root.refresh.refreshUI();
      return;
    }
    if (opts.refreshData === true && root.refresh && typeof root.refresh.refreshData === "function") {
      await root.refresh.refreshData();
    }
  }

  async function listChatThreads(options) {
    const opts = options || {};
    return _requestChatRoute("/api/chat/threads", {
      method: "GET",
      stream: opts.stream === true,
      onEvent: typeof opts.onStreamEvent === "function" ? opts.onStreamEvent : null,
      signal: opts.signal,
    });
  }

  async function loadChatThread(threadId, options) {
    const opts = options || {};
    const path = _threadRoutePath(threadId, "load", opts.activate !== false);
    if (!path) {
      return { ok: false, error: "Chat thread id is required." };
    }
    const response = await _requestChatRoute(path, {
      method: "POST",
      body: {},
      stream: opts.stream === true,
      onEvent: typeof opts.onStreamEvent === "function" ? opts.onStreamEvent : null,
      signal: opts.signal,
    });
    if (response && response.ok === false) {
      return response;
    }
    await _refreshAfterChatRoute({
      refreshData: opts.refreshData === true,
      refreshUI: opts.refreshUI !== false,
    });
    return response;
  }

  async function saveChatThread(threadId, payload, options) {
    const opts = options || {};
    const path = _threadRoutePath(threadId, "save", opts.activate === true);
    if (!path) {
      return { ok: false, error: "Chat thread id is required." };
    }
    const body = payload && typeof payload === "object" ? payload : {};
    const response = await _requestChatRoute(path, {
      method: "PUT",
      body,
      stream: opts.stream === true,
      onEvent: typeof opts.onStreamEvent === "function" ? opts.onStreamEvent : null,
      signal: opts.signal,
    });
    if (response && response.ok === false) {
      return response;
    }
    await _refreshAfterChatRoute({
      refreshData: opts.refreshData === true,
      refreshUI: opts.refreshUI === true,
    });
    return response;
  }

  async function executeAction(actionId, payload, options) {
    if (!actionId) {
      setRunStatus("error", dom.buildErrorLines("No action selected."));
      return { ok: false, error: "No action selected." };
    }
    if (root.setup && typeof root.setup.confirmProceed === "function") {
      const allowed = await root.setup.confirmProceed();
      if (!allowed) {
        return { ok: false, error: "Missing secrets." };
      }
    }
    state.setLastAction({ id: actionId, payload: payload || {} });
    setRunButtonBusy(true);
    setRunStatus("running", [RUNNING_LABEL]);
    try {
      const opts = options || {};
      const useStreaming = opts.stream !== false && net && typeof net.postSse === "function";
      const onStreamEvent = typeof opts.onStreamEvent === "function" ? opts.onStreamEvent : null;
      let data;
      if (useStreaming) {
        try {
          activeController = new AbortController();
          data = await net.postSse("/api/action/stream", { id: actionId, payload }, {
            signal: activeController.signal,
            onEvent: (event) => {
              if (onStreamEvent) onStreamEvent(event);
            },
          });
        } catch (streamErr) {
          const cancelled = _isAbortError(streamErr);
          if (cancelled) throw streamErr;
          data = await net.postJson("/api/action", { id: actionId, payload });
        }
      } else {
        data = await net.postJson("/api/action", { id: actionId, payload });
      }
      if (data && data.ui && root.refresh && root.refresh.applyManifest) {
        root.refresh.applyManifest(data.ui);
      }
      if (actionResult && typeof actionResult.applyActionResult === "function") {
        actionResult.applyActionResult(data);
      }
      if (root.refresh && typeof root.refresh.refreshData === "function") {
        root.refresh.refreshData();
      }
      if (root.refresh && typeof root.refresh.refreshSession === "function") {
        root.refresh.refreshSession();
      }
      if (root.refresh && typeof root.refresh.refreshDiagnostics === "function") {
        root.refresh.refreshDiagnostics();
      }
      if (data && data.ok === false) {
        setRunStatus("error", dom.buildErrorLines(data));
      } else {
        setRunStatus("success", [SUCCESS_LABEL]);
      }
      return data;
    } catch (err) {
      const cancelled = _isAbortError(err);
      const detail = cancelled ? "Streaming cancelled." : err && err.message ? err.message : String(err);
      if (actionResult && typeof actionResult.applyActionResult === "function") {
        actionResult.applyActionResult({ ok: false, error: detail, kind: "engine", cancelled });
      }
      setRunStatus("error", dom.buildErrorLines(detail));
      return { ok: false, error: detail, cancelled };
    } finally {
      activeController = null;
      setRunButtonBusy(false);
      if (root.menu && root.menu.updateMenuState) root.menu.updateMenuState();
    }
  }

  function cancelActiveAction() {
    if (!activeController) return false;
    activeController.abort();
    return true;
  }

  async function runSeedAction() {
    const seedActionId = state.getSeedActionId();
    if (!seedActionId) {
      setRunStatus("error", dom.buildErrorLines("No run action found."));
      return;
    }
    await executeAction(seedActionId, {});
  }

  async function runResetAction() {
    const resetActionId = state.getResetActionId();
    if (!resetActionId) {
      setRunStatus("error", dom.buildErrorLines("No reset action found."));
      return;
    }
    await executeAction(resetActionId, {});
  }

  async function replayLastAction() {
    const lastAction = state.getLastAction();
    if (!lastAction) {
      setRunStatus("error", dom.buildErrorLines("No prior action to replay."));
      return;
    }
    await executeAction(lastAction.id, lastAction.payload || {});
  }

  function exportTraces() {
    const traces = state.getCachedTraces() || [];
    if (!traces.length) {
      setRunStatus("error", dom.buildErrorLines("No traces available to export."));
      return;
    }
    const payload = JSON.stringify(traces, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "namel3ss-traces.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setRunStatus("success", ["Trace exported."]);
  }

  function setupRunButton() {
    const button = getRunButton();
    if (!button) return;
    runLabel = button.textContent || runLabel;
    button.textContent = runLabel;
    button.disabled = true;
    button.onclick = () => runSeedAction();
  }

  run.setupRunButton = setupRunButton;
  run.updateSeedAction = updateSeedAction;
  run.updateResetAction = updateResetAction;
  run.executeAction = executeAction;
  run.runSeedAction = runSeedAction;
  run.runResetAction = runResetAction;
  run.replayLastAction = replayLastAction;
  run.exportTraces = exportTraces;
  run.cancelActiveAction = cancelActiveAction;
  run.listChatThreads = listChatThreads;
  run.loadChatThread = loadChatThread;
  run.saveChatThread = saveChatThread;

  window.executeAction = executeAction;
})();
