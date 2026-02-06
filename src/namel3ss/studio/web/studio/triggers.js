(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const triggers = root.triggers || (root.triggers = {});

  function buildRow(item) {
    const row = document.createElement("div");
    row.className = "list-item";
    row.textContent = `${item.type} ${item.name} pattern=${item.pattern} flow=${item.flow}`;
    return row;
  }

  function buildControls(statusNode, refresh) {
    const section = document.createElement("div");
    section.className = "panel-section";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Register trigger";
    section.appendChild(title);

    const typeInput = document.createElement("input");
    typeInput.type = "text";
    typeInput.placeholder = "webhook | upload | timer | queue";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.placeholder = "trigger name";
    const patternInput = document.createElement("input");
    patternInput.type = "text";
    patternInput.placeholder = "path, directory, cron, or queue key";
    const flowInput = document.createElement("input");
    flowInput.type = "text";
    flowInput.placeholder = "flow name";

    const row = document.createElement("div");
    row.className = "ui-buttons";
    const registerBtn = document.createElement("button");
    registerBtn.className = "btn ghost";
    registerBtn.textContent = "Register";
    row.appendChild(registerBtn);

    registerBtn.addEventListener("click", async () => {
      statusNode.classList.remove("error");
      statusNode.textContent = "";
      try {
        const payload = await net.postJson("/api/triggers", {
          action: "register",
          type: typeInput.value.trim(),
          name: nameInput.value.trim(),
          pattern: patternInput.value.trim(),
          flow: flowInput.value.trim(),
        });
        statusNode.textContent = `Trigger saved. total=${payload.count || 0}`;
        await refresh();
      } catch (err) {
        statusNode.textContent = err && err.message ? err.message : "Register failed.";
        statusNode.classList.add("error");
      }
    });

    section.appendChild(typeInput);
    section.appendChild(nameInput);
    section.appendChild(patternInput);
    section.appendChild(flowInput);
    section.appendChild(row);
    return section;
  }

  async function renderTriggers() {
    const panel = document.getElementById("triggers");
    if (!panel) return;
    panel.innerHTML = "";

    const stack = document.createElement("div");
    stack.className = "panel-stack";

    const status = document.createElement("div");
    status.className = "preview-hint";
    const list = document.createElement("div");
    list.className = "list";

    async function refresh() {
      list.innerHTML = "";
      status.textContent = "";
      status.classList.remove("error");
      try {
        const payload = await net.fetchJson("/api/triggers");
        const items = payload && Array.isArray(payload.items) ? payload.items : [];
        if (!items.length) {
          list.appendChild(dom.buildEmpty("No triggers configured yet."));
          return;
        }
        items.forEach((item) => list.appendChild(buildRow(item)));
      } catch (err) {
        status.textContent = err && err.message ? err.message : "Could not load triggers.";
        status.classList.add("error");
      }
    }

    stack.appendChild(buildControls(status, refresh));
    stack.appendChild(status);
    stack.appendChild(list);
    panel.appendChild(stack);

    await refresh();
  }

  triggers.renderTriggers = renderTriggers;
})();
