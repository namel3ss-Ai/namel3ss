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

  async function executeAction(actionId, payload) {
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
      const data = await net.postJson("/api/action", { id: actionId, payload });
      if (data && data.ui && root.refresh && root.refresh.applyManifest) {
        root.refresh.applyManifest(data.ui);
      }
      if (actionResult && typeof actionResult.applyActionResult === "function") {
        actionResult.applyActionResult(data);
      }
      if (data && data.ok === false) {
        setRunStatus("error", dom.buildErrorLines(data));
      } else {
        setRunStatus("success", [SUCCESS_LABEL]);
      }
      return data;
    } catch (err) {
      const detail = err && err.message ? err.message : String(err);
      if (actionResult && typeof actionResult.applyActionResult === "function") {
        actionResult.applyActionResult({ ok: false, error: detail, kind: "engine" });
      }
      setRunStatus("error", dom.buildErrorLines(detail));
      return { ok: false, error: detail };
    } finally {
      setRunButtonBusy(false);
      if (root.menu && root.menu.updateMenuState) root.menu.updateMenuState();
    }
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

  window.executeAction = executeAction;
})();
