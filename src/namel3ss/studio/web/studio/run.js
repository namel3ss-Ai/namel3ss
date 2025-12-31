(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const run = root.run || (root.run = {});

  const RUNNING_LABEL = "Running...";
  const SUCCESS_LABEL = "Run complete.";
  let runLabel = "Run";

  const PREFERRED_SEED_FLOWS = ["seed", "seed_data", "seed_demo", "demo_seed", "seed_customers"];

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

  async function executeAction(actionId, payload) {
    if (!actionId) {
      setRunStatus("error", dom.buildErrorLines("No action selected."));
      return { ok: false, error: "No action selected." };
    }
    setRunButtonBusy(true);
    setRunStatus("running", [RUNNING_LABEL]);
    try {
      const data = await net.postJson("/api/action", { id: actionId, payload });
      if (data && data.ui && root.refresh && root.refresh.applyManifest) {
        root.refresh.applyManifest(data.ui);
      }
      if (data && Array.isArray(data.traces) && window.renderTraces) {
        window.renderTraces(data.traces);
      }
      if (data && data.ok === false) {
        setRunStatus("error", dom.buildErrorLines(data));
      } else {
        setRunStatus("success", [SUCCESS_LABEL]);
      }
      return data;
    } catch (err) {
      const detail = err && err.message ? err.message : String(err);
      setRunStatus("error", dom.buildErrorLines(detail));
      return { ok: false, error: detail };
    } finally {
      setRunButtonBusy(false);
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
  run.executeAction = executeAction;
  run.runSeedAction = runSeedAction;

  window.executeAction = executeAction;
})();
