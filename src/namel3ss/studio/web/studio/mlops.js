(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const mlops = root.mlops || (root.mlops = {});

  function line(text) {
    const row = document.createElement("div");
    row.className = "status-line";
    row.textContent = text;
    return row;
  }

  function modelRow(item) {
    const row = document.createElement("div");
    row.className = "list-item";
    const metrics = item.metrics && typeof item.metrics === "object" ? item.metrics : {};
    const metricsText = Object.keys(metrics)
      .sort()
      .map((key) => `${key}=${metrics[key]}`)
      .join(" ");
    row.textContent = `${item.name}@${item.version} artifact=${item.artifact_uri || ""} ${metricsText}`.trim();
    return row;
  }

  async function renderMLOps() {
    const panel = document.getElementById("mlops");
    if (!panel) return;
    panel.innerHTML = "";

    const stack = document.createElement("div");
    stack.className = "panel-stack";

    const controls = document.createElement("div");
    controls.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "MLOps";
    controls.appendChild(title);

    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.placeholder = "model name";
    const versionInput = document.createElement("input");
    versionInput.type = "text";
    versionInput.placeholder = "version";
    const artifactInput = document.createElement("input");
    artifactInput.type = "text";
    artifactInput.placeholder = "artifact uri";

    const status = document.createElement("div");
    status.className = "preview-hint";

    const actions = document.createElement("div");
    actions.className = "ui-buttons";
    const refreshBtn = document.createElement("button");
    refreshBtn.className = "btn ghost";
    refreshBtn.textContent = "Refresh";
    const registerBtn = document.createElement("button");
    registerBtn.className = "btn ghost";
    registerBtn.textContent = "Register";
    const getBtn = document.createElement("button");
    getBtn.className = "btn ghost";
    getBtn.textContent = "Get";
    const retrainBtn = document.createElement("button");
    retrainBtn.className = "btn ghost";
    retrainBtn.textContent = "Sync retrain";

    [refreshBtn, registerBtn, getBtn, retrainBtn].forEach((button) => actions.appendChild(button));

    controls.appendChild(nameInput);
    controls.appendChild(versionInput);
    controls.appendChild(artifactInput);
    controls.appendChild(actions);
    controls.appendChild(status);

    const summary = document.createElement("div");
    summary.className = "panel-section";
    const summaryTitle = document.createElement("div");
    summaryTitle.className = "panel-section-title";
    summaryTitle.textContent = "Registry status";
    const summaryLines = document.createElement("div");
    summaryLines.className = "status-lines";
    summary.appendChild(summaryTitle);
    summary.appendChild(summaryLines);

    const list = document.createElement("div");
    list.className = "list";

    stack.appendChild(controls);
    stack.appendChild(summary);
    stack.appendChild(list);
    panel.appendChild(stack);

    async function loadStatus() {
      const payload = await net.fetchJson("/api/mlops");
      summaryLines.innerHTML = "";
      summaryLines.appendChild(line(`configured ${payload.configured}`));
      summaryLines.appendChild(line(`models ${payload.count || 0}`));

      list.innerHTML = "";
      const models = payload && Array.isArray(payload.models) ? payload.models : [];
      if (!models.length) {
        list.appendChild(dom.buildEmpty("No model registry entries yet."));
      } else {
        models.forEach((item) => list.appendChild(modelRow(item)));
      }
    }

    async function runRegister() {
      status.classList.remove("error");
      status.textContent = "";
      const payload = await net.postJson("/api/mlops", {
        action: "register_model",
        name: nameInput.value.trim(),
        version: versionInput.value.trim(),
        artifact_uri: artifactInput.value.trim(),
        experiment_id: "studio",
      });
      status.textContent = payload.queued ? "Registered and queued for sync." : "Registered in registry.";
      await loadStatus();
    }

    async function runGet() {
      status.classList.remove("error");
      status.textContent = "";
      const payload = await net.postJson("/api/mlops", {
        action: "get_model",
        name: nameInput.value.trim(),
        version: versionInput.value.trim(),
      });
      if (!payload.ok) {
        status.textContent = payload.error || "Model not found.";
        status.classList.add("error");
        return;
      }
      const model = payload.model || {};
      status.textContent = `Found ${model.name}@${model.version}`;
    }

    async function runRetrainSync() {
      status.classList.remove("error");
      status.textContent = "";
      const payload = await net.postJson("/api/mlops", { action: "retrain_sync" });
      status.textContent = `Created ${payload.count || 0} retrain experiments. queued=${payload.queued || 0}`;
      await loadStatus();
    }

    refreshBtn.addEventListener("click", () => loadStatus());
    registerBtn.addEventListener("click", () => runRegister().catch((err) => {
      status.textContent = err && err.message ? err.message : "Register failed.";
      status.classList.add("error");
    }));
    getBtn.addEventListener("click", () => runGet().catch((err) => {
      status.textContent = err && err.message ? err.message : "Lookup failed.";
      status.classList.add("error");
    }));
    retrainBtn.addEventListener("click", () => runRetrainSync().catch((err) => {
      status.textContent = err && err.message ? err.message : "Sync failed.";
      status.classList.add("error");
    }));

    try {
      await loadStatus();
    } catch (err) {
      panel.innerHTML = "";
      dom.showError(panel, err && err.message ? err.message : "MLOps panel failed.");
    }
  }

  mlops.renderMLOps = renderMLOps;
})();
