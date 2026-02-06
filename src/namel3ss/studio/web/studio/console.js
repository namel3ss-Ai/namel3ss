(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const consolePanel = root.console || (root.console = {});

  let validateTimer = null;

  function buildDefinitionSummary(definitions) {
    const wrap = document.createElement("div");
    wrap.className = "panel-section";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Definitions";
    wrap.appendChild(title);

    const lines = document.createElement("div");
    lines.className = "status-lines";
    const mapping = [
      ["routes", "Routes"],
      ["flows", "Flows"],
      ["prompts", "Prompts"],
      ["datasets", "Datasets"],
      ["ai_flows", "AI flows"],
    ];
    mapping.forEach(([key, label]) => {
      const items = definitions && Array.isArray(definitions[key]) ? definitions[key] : [];
      const line = document.createElement("div");
      line.className = "status-line";
      line.textContent = `${label}: ${items.length}`;
      lines.appendChild(line);
    });
    wrap.appendChild(lines);
    return wrap;
  }

  function buildLintList(lint) {
    const wrap = document.createElement("div");
    wrap.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Lint";
    wrap.appendChild(title);

    const findings = lint && Array.isArray(lint.findings) ? lint.findings : [];
    if (!findings.length) {
      wrap.appendChild(dom.buildEmpty("No lint findings."));
      return wrap;
    }

    const list = document.createElement("div");
    list.className = "list";
    findings.forEach((finding) => {
      const row = document.createElement("div");
      row.className = "list-item";
      const code = finding && finding.code ? `${finding.code}: ` : "";
      const line = finding && finding.line ? ` (line ${finding.line})` : "";
      row.textContent = `${code}${finding.message || "Lint issue"}${line}`;
      list.appendChild(row);
    });
    wrap.appendChild(list);
    return wrap;
  }

  function setValidationStatus(target, payload) {
    if (!target) return;
    if (!payload || payload.ok === false) {
      target.textContent = payload && payload.error ? payload.error : "Validation failed.";
      target.classList.add("error");
      return;
    }
    const count = Number(payload.count || 0);
    target.textContent = count ? `${count} lint findings` : "Validation passed";
    target.classList.toggle("error", count > 0);
  }

  async function renderConsole() {
    const panel = document.getElementById("console");
    if (!panel) return;
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";
    wrapper.appendChild(dom.buildEmpty("Loading console..."));
    panel.appendChild(wrapper);

    try {
      const payload = await net.fetchJson("/api/console");
      if (!payload || payload.ok === false) {
        panel.innerHTML = "";
        dom.showError(panel, payload && payload.error ? payload.error : "Console failed to load.");
        return;
      }

      panel.innerHTML = "";
      const layout = document.createElement("div");
      layout.className = "panel-stack";

      const controls = document.createElement("div");
      controls.className = "panel-section";
      const title = document.createElement("div");
      title.className = "panel-section-title";
      title.textContent = "Console";
      controls.appendChild(title);

      const status = document.createElement("div");
      status.className = "status-lines";
      const statusLine = document.createElement("div");
      statusLine.className = "status-line";
      statusLine.textContent = "Edit app.ai, models.yaml and feedback.yaml with live validation.";
      status.appendChild(statusLine);
      controls.appendChild(status);

      const actionRow = document.createElement("div");
      actionRow.className = "ui-buttons";
      const validateBtn = document.createElement("button");
      validateBtn.className = "btn ghost";
      validateBtn.textContent = "Validate";
      const saveBtn = document.createElement("button");
      saveBtn.className = "btn primary";
      saveBtn.textContent = "Save";
      const runBtn = document.createElement("button");
      runBtn.className = "btn ghost";
      runBtn.textContent = "Run";
      actionRow.appendChild(validateBtn);
      actionRow.appendChild(saveBtn);
      actionRow.appendChild(runBtn);
      controls.appendChild(actionRow);

      const validateStatus = document.createElement("div");
      validateStatus.className = "preview-hint";
      controls.appendChild(validateStatus);

      layout.appendChild(controls);
      layout.appendChild(buildDefinitionSummary(payload.definitions || {}));

      const sourceSection = document.createElement("div");
      sourceSection.className = "panel-section";
      const sourceTitle = document.createElement("div");
      sourceTitle.className = "panel-section-title";
      sourceTitle.textContent = "app.ai";
      const sourceInput = document.createElement("textarea");
      sourceInput.className = "code-block";
      sourceInput.style.minHeight = "220px";
      sourceInput.value = payload.source || "";
      sourceSection.appendChild(sourceTitle);
      sourceSection.appendChild(sourceInput);
      layout.appendChild(sourceSection);

      const modelsSection = document.createElement("div");
      modelsSection.className = "panel-section";
      const modelsTitle = document.createElement("div");
      modelsTitle.className = "panel-section-title";
      modelsTitle.textContent = "models.yaml";
      const modelsInput = document.createElement("textarea");
      modelsInput.className = "code-block";
      modelsInput.style.minHeight = "140px";
      modelsInput.value = (payload.files && payload.files.models_yaml) || "";
      modelsSection.appendChild(modelsTitle);
      modelsSection.appendChild(modelsInput);
      layout.appendChild(modelsSection);

      const feedbackSection = document.createElement("div");
      feedbackSection.className = "panel-section";
      const feedbackTitle = document.createElement("div");
      feedbackTitle.className = "panel-section-title";
      feedbackTitle.textContent = "feedback.yaml";
      const feedbackInput = document.createElement("textarea");
      feedbackInput.className = "code-block";
      feedbackInput.style.minHeight = "120px";
      feedbackInput.value = (payload.files && payload.files.feedback_yaml) || "";
      feedbackSection.appendChild(feedbackTitle);
      feedbackSection.appendChild(feedbackInput);
      layout.appendChild(feedbackSection);

      layout.appendChild(buildLintList(payload.lint || {}));
      panel.appendChild(layout);

      const runValidation = async () => {
        setValidationStatus(validateStatus, { ok: true, count: 0 });
        try {
          const resp = await net.postJson("/api/console/validate", {
            source: sourceInput.value,
          });
          setValidationStatus(validateStatus, resp);
        } catch (err) {
          setValidationStatus(validateStatus, { ok: false, error: err && err.message ? err.message : "Validation failed." });
        }
      };

      const queueValidation = () => {
        if (validateTimer) clearTimeout(validateTimer);
        validateTimer = setTimeout(() => {
          runValidation();
        }, 350);
      };

      sourceInput.addEventListener("input", queueValidation);
      validateBtn.addEventListener("click", () => runValidation());
      saveBtn.addEventListener("click", async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";
        try {
          const resp = await net.postJson("/api/console/save", {
            source: sourceInput.value,
            models_yaml: modelsInput.value,
            feedback_yaml: feedbackInput.value,
          });
          setValidationStatus(validateStatus, resp);
          if (resp && resp.ok && root.refresh && typeof root.refresh.refreshUI === "function") {
            await root.refresh.refreshUI();
            await root.refresh.refreshSummary();
          }
        } catch (err) {
          setValidationStatus(validateStatus, { ok: false, error: err && err.message ? err.message : "Save failed." });
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save";
        }
      });

      runBtn.addEventListener("click", () => {
        if (root.run && typeof root.run.runSeedAction === "function") {
          root.run.runSeedAction();
        }
      });
    } catch (err) {
      panel.innerHTML = "";
      dom.showError(panel, err && err.message ? err.message : "Console failed to load.");
    }
  }

  consolePanel.renderConsole = renderConsole;
})();
