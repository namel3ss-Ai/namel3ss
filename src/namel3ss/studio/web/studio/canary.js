(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const canary = root.canary || (root.canary = {});

  function buildSummary(summary) {
    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Canary summary";
    section.appendChild(title);

    if (!summary.length) {
      section.appendChild(dom.buildEmpty("No canary or shadow comparisons yet."));
      return section;
    }

    const list = document.createElement("div");
    list.className = "list";
    summary.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "list-item";
      row.textContent = (
        `${entry.primary_model} vs ${entry.candidate_model} ` +
        `mode=${entry.mode} runs=${entry.runs} ` +
        `candidate_wins=${entry.candidate_wins} primary_wins=${entry.primary_wins} ties=${entry.ties}`
      );
      list.appendChild(row);
    });
    section.appendChild(list);
    return section;
  }

  function buildConfig(models, statusNode) {
    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Configure canary";
    section.appendChild(title);

    if (!models.length) {
      section.appendChild(dom.buildEmpty("No models configured in models.yaml."));
      return section;
    }

    const selectPrimary = document.createElement("select");
    const selectCandidate = document.createElement("select");
    models.forEach((model) => {
      const option = document.createElement("option");
      option.value = model.name;
      option.textContent = model.name;
      selectPrimary.appendChild(option);
      const optionCandidate = document.createElement("option");
      optionCandidate.value = model.name;
      optionCandidate.textContent = model.name;
      selectCandidate.appendChild(optionCandidate);
    });

    const offOption = document.createElement("option");
    offOption.value = "off";
    offOption.textContent = "off";
    selectCandidate.appendChild(offOption);

    const fractionInput = document.createElement("input");
    fractionInput.type = "number";
    fractionInput.min = "0";
    fractionInput.max = "1";
    fractionInput.step = "0.01";
    fractionInput.value = "0.1";

    const shadowToggle = document.createElement("input");
    shadowToggle.type = "checkbox";
    const shadowLabel = document.createElement("label");
    shadowLabel.textContent = "Shadow compare";
    shadowLabel.prepend(shadowToggle);

    const applyBtn = document.createElement("button");
    applyBtn.className = "btn ghost";
    applyBtn.textContent = "Apply";

    const row = document.createElement("div");
    row.className = "ui-buttons";
    row.appendChild(selectPrimary);
    row.appendChild(selectCandidate);
    row.appendChild(fractionInput);
    row.appendChild(shadowLabel);
    row.appendChild(applyBtn);
    section.appendChild(row);

    applyBtn.addEventListener("click", async () => {
      applyBtn.disabled = true;
      applyBtn.textContent = "Applying...";
      try {
        await net.postJson("/api/canary/config", {
          primary_model: selectPrimary.value,
          candidate_model: selectCandidate.value,
          fraction: Number(fractionInput.value || 0),
          shadow: shadowToggle.checked,
        });
        statusNode.textContent = "Canary config updated.";
        statusNode.classList.remove("error");
        renderCanary();
      } catch (err) {
        statusNode.textContent = err && err.message ? err.message : "Canary config failed.";
        statusNode.classList.add("error");
      } finally {
        applyBtn.disabled = false;
        applyBtn.textContent = "Apply";
      }
    });

    return section;
  }

  async function renderCanary() {
    const panel = document.getElementById("canary");
    if (!panel) return;
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";
    wrapper.appendChild(dom.buildEmpty("Loading canary data..."));
    panel.appendChild(wrapper);

    try {
      const payload = await net.fetchJson("/api/canary");
      if (!payload || payload.ok === false) {
        panel.innerHTML = "";
        dom.showError(panel, payload && payload.error ? payload.error : "Canary panel failed to load.");
        return;
      }
      panel.innerHTML = "";
      const layout = document.createElement("div");
      layout.className = "panel-stack";
      const summary = Array.isArray(payload.summary) ? payload.summary : [];
      const models = Array.isArray(payload.models) ? payload.models : [];
      const status = document.createElement("div");
      status.className = "preview-hint";
      layout.appendChild(buildConfig(models, status));
      layout.appendChild(buildSummary(summary));
      layout.appendChild(status);
      panel.appendChild(layout);
    } catch (err) {
      panel.innerHTML = "";
      dom.showError(panel, err && err.message ? err.message : "Canary panel failed to load.");
    }
  }

  canary.renderCanary = renderCanary;
})();
