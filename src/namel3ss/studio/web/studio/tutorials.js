(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const tutorials = root.tutorials || (root.tutorials = {});

  async function loadTutorials() {
    return net.postJson("/api/tutorials", { action: "list" });
  }

  async function runTutorial(slug) {
    return net.postJson("/api/tutorials", { action: "run", slug, auto: true });
  }

  function buildCard(item, status) {
    const card = document.createElement("div");
    card.className = "list-item";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = `${item.slug} - ${item.title}`;
    card.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "status-lines";
    const lines = [
      `steps ${item.steps}`,
      `requires ${item.requires}`,
      `status ${item.completed ? "done" : "todo"}`,
      `last passed ${item.last_passed || 0}`,
      Array.isArray(item.tags) ? `tags ${item.tags.join(", ")}` : "",
    ];
    lines.forEach((line) => {
      if (!line) return;
      const node = document.createElement("div");
      node.className = "status-line";
      node.textContent = line;
      meta.appendChild(node);
    });
    card.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "ui-buttons";
    const runBtn = document.createElement("button");
    runBtn.className = "btn ghost";
    runBtn.textContent = "Run";
    runBtn.addEventListener("click", async () => {
      runBtn.disabled = true;
      runBtn.textContent = "Running...";
      try {
        const payload = await runTutorial(item.slug);
        status.classList.remove("error");
        status.textContent = `Tutorial ${item.slug}: ${payload.passed_steps}/${payload.step_count} passed.`;
        renderTutorials();
      } catch (err) {
        status.classList.add("error");
        status.textContent = err && err.message ? err.message : "Tutorial run failed.";
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = "Run";
      }
    });
    actions.appendChild(runBtn);
    card.appendChild(actions);
    return card;
  }

  async function renderTutorials() {
    const panel = document.getElementById("tutorials");
    if (!panel) return;
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";

    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Interactive tutorials";
    section.appendChild(title);

    const status = document.createElement("div");
    status.className = "preview-hint";
    section.appendChild(status);

    const list = document.createElement("div");
    list.className = "list";

    wrapper.appendChild(section);
    wrapper.appendChild(list);
    panel.appendChild(wrapper);

    try {
      const payload = await loadTutorials();
      const items = payload && Array.isArray(payload.items) ? payload.items : [];
      if (!items.length) {
        list.appendChild(dom.buildEmpty("No tutorials found."));
        return;
      }
      items.forEach((item) => {
        list.appendChild(buildCard(item, status));
      });
    } catch (err) {
      status.classList.add("error");
      status.textContent = err && err.message ? err.message : "Could not load tutorials.";
    }
  }

  tutorials.renderTutorials = renderTutorials;
})();
