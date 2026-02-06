(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const versioning = root.versioning || (root.versioning = {});

  function buildRow(item) {
    const row = document.createElement("div");
    row.className = "list-item";
    row.textContent = `${item.kind} ${item.entity}@${item.version} status=${item.status}`;
    if (item.replacement) {
      row.textContent += ` replacement=${item.replacement}`;
    }
    if (item.deprecation_date) {
      row.textContent += ` eol=${item.deprecation_date}`;
    }
    return row;
  }

  function buildControls(statusNode, refresh) {
    const section = document.createElement("div");
    section.className = "panel-section";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Manage versions";
    section.appendChild(title);

    const entity = document.createElement("input");
    entity.type = "text";
    entity.placeholder = "flow:summarise";
    const version = document.createElement("input");
    version.type = "text";
    version.placeholder = "2.0";
    const replacement = document.createElement("input");
    replacement.type = "text";
    replacement.placeholder = "replacement version (optional)";
    const eol = document.createElement("input");
    eol.type = "text";
    eol.placeholder = "eol date YYYY-MM-DD";

    const row = document.createElement("div");
    row.className = "ui-buttons";

    const addBtn = document.createElement("button");
    addBtn.className = "btn ghost";
    addBtn.textContent = "Add";
    const deprecateBtn = document.createElement("button");
    deprecateBtn.className = "btn ghost";
    deprecateBtn.textContent = "Deprecate";
    const removeBtn = document.createElement("button");
    removeBtn.className = "btn ghost";
    removeBtn.textContent = "Remove";

    [addBtn, deprecateBtn, removeBtn].forEach((button) => row.appendChild(button));

    async function runAction(action) {
      statusNode.classList.remove("error");
      statusNode.textContent = "";
      try {
        const payload = await net.postJson("/api/versioning", {
          action,
          entity: entity.value.trim(),
          version: version.value.trim(),
          replacement: replacement.value.trim(),
          deprecation_date: eol.value.trim(),
        });
        statusNode.textContent = `${action} complete. total=${payload.count || 0}`;
        await refresh();
      } catch (err) {
        statusNode.textContent = err && err.message ? err.message : `${action} failed.`;
        statusNode.classList.add("error");
      }
    }

    addBtn.addEventListener("click", () => runAction("add"));
    deprecateBtn.addEventListener("click", () => runAction("deprecate"));
    removeBtn.addEventListener("click", () => runAction("remove"));

    section.appendChild(entity);
    section.appendChild(version);
    section.appendChild(replacement);
    section.appendChild(eol);
    section.appendChild(row);

    return section;
  }

  async function renderVersioning() {
    const panel = document.getElementById("versioning");
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
      try {
        const payload = await net.fetchJson("/api/versioning");
        const items = payload && Array.isArray(payload.items) ? payload.items : [];
        if (!items.length) {
          list.appendChild(dom.buildEmpty("No versions configured yet."));
          return;
        }
        items.forEach((item) => list.appendChild(buildRow(item)));
      } catch (err) {
        list.innerHTML = "";
        status.textContent = err && err.message ? err.message : "Could not load versioning.";
        status.classList.add("error");
      }
    }

    stack.appendChild(buildControls(status, refresh));
    stack.appendChild(status);
    stack.appendChild(list);
    panel.appendChild(stack);

    await refresh();
  }

  versioning.renderVersioning = renderVersioning;
})();
