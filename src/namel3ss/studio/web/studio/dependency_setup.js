(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const net = root.net;
  const dependencySetup = root.dependencySetup || (root.dependencySetup = {});

  let cachedPayload = null;

  function normalizeStatus(payload) {
    if (!payload || payload.ok === false || !payload.status) return null;
    return payload.status;
  }

  function normalizeToken(value) {
    return String(value || "").trim().toLowerCase();
  }

  function dependencySpec(entry, type) {
    if (!entry || typeof entry !== "object") return "";
    const name = String(entry.name || "").trim();
    const version = String(entry.version || "").trim();
    if (!name) return "";
    if (type === "system") {
      if (!version || version === "*") return name;
      return `${name}@${version}`;
    }
    if (!version || version === "*") return name;
    return `${name}==${version}`;
  }

  function matchesSearch(entry, search) {
    if (!search) return true;
    const token = normalizeToken(search);
    const values = [entry.name, entry.version, entry.source, entry.spec];
    return values.some((value) => normalizeToken(value).includes(token));
  }

  function buildCounts(status) {
    const container = document.createElement("div");
    container.className = "provider-settings";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Dependencies";
    container.appendChild(title);

    const summary = document.createElement("div");
    summary.className = "provider-settings-help";
    summary.textContent = [
      `packs: ${Number(status.packages_count || 0)}`,
      `python: ${Number(status.runtime_python_count || 0)}`,
      `system: ${Number(status.runtime_system_count || 0)}`,
    ].join(" · ");
    container.appendChild(summary);

    const lockfile = document.createElement("div");
    lockfile.className = "provider-settings-help";
    lockfile.textContent = `lockfile: ${status.lockfile_path || "missing"}`;
    container.appendChild(lockfile);

    const pythonLockfile = document.createElement("div");
    pythonLockfile.className = "provider-settings-help";
    pythonLockfile.textContent = `python lockfile: ${status.python_lockfile_path || "missing"}`;
    container.appendChild(pythonLockfile);

    return container;
  }

  function buildTree(status, search) {
    const wrapper = document.createElement("div");
    wrapper.className = "provider-settings";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Dependency graph";
    wrapper.appendChild(title);

    const tree = status && status.tree && Array.isArray(status.tree.package_tree)
      ? status.tree.package_tree
      : [];
    const filteredTree = tree.filter((line) => normalizeToken(line).includes(normalizeToken(search)));

    if (!filteredTree.length) {
      const empty = document.createElement("div");
      empty.className = "provider-settings-help";
      empty.textContent = tree.length ? "No graph nodes match search." : "No package graph available.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const pre = document.createElement("pre");
    pre.className = "code-block";
    pre.textContent = filteredTree.join("\n");
    wrapper.appendChild(pre);
    return wrapper;
  }

  function buildRuntimeDependencies(status, search, runAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "provider-settings";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Runtime dependencies";
    wrapper.appendChild(title);

    const tree = status && status.tree ? status.tree : {};
    const pythonRows = Array.isArray(tree.runtime_python)
      ? tree.runtime_python.map((entry) => ({
        ...entry,
        type: "python",
        spec: dependencySpec(entry, "python"),
      }))
      : [];
    const systemRows = Array.isArray(tree.runtime_system)
      ? tree.runtime_system.map((entry) => ({
        ...entry,
        type: "system",
        spec: dependencySpec(entry, "system"),
      }))
      : [];
    const rows = [...pythonRows, ...systemRows].filter((entry) => matchesSearch(entry, search));

    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "provider-settings-help";
      empty.textContent = "No runtime dependencies match search.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const list = document.createElement("div");
    list.className = "provider-settings-list";
    rows.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "provider-settings-row";

      const info = document.createElement("div");
      info.className = "provider-settings-help";
      const version = entry.version && entry.version !== "*" ? ` ${entry.version}` : "";
      info.textContent = `${entry.type}: ${entry.name}${version}`;
      row.appendChild(info);

      const removeButton = document.createElement("button");
      removeButton.type = "button";
      removeButton.className = "btn ghost";
      removeButton.textContent = "Remove";
      removeButton.onclick = () => {
        const action = entry.type === "python" ? "remove_python" : "remove_system";
        runAction(action, { spec: entry.spec });
      };
      row.appendChild(removeButton);
      list.appendChild(row);
    });
    wrapper.appendChild(list);
    return wrapper;
  }

  function buildActions(runAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "provider-settings-actions";

    const installButton = document.createElement("button");
    installButton.type = "button";
    installButton.className = "btn ghost";
    installButton.textContent = "Install dependencies";

    const updateButton = document.createElement("button");
    updateButton.type = "button";
    updateButton.className = "btn ghost";
    updateButton.textContent = "Update dependencies";

    const status = document.createElement("div");
    status.className = "provider-settings-status";

    async function run(action) {
      status.textContent = `${action}...`;
      installButton.disabled = true;
      updateButton.disabled = true;
      try {
        const payload = await runAction(action, {});
        if (payload && payload.ok === false) {
          status.textContent = payload.error || "Dependency action failed.";
        } else if (payload && payload.status === "fail") {
          status.textContent = payload.reason || "Dependency action reported failures.";
        } else {
          status.textContent = "Done.";
        }
      } catch (err) {
        status.textContent = err && err.message ? err.message : "Dependency action failed.";
      } finally {
        installButton.disabled = false;
        updateButton.disabled = false;
      }
    }

    installButton.onclick = () => run("install");
    updateButton.onclick = () => run("update");

    wrapper.appendChild(installButton);
    wrapper.appendChild(updateButton);
    wrapper.appendChild(status);
    return wrapper;
  }

  function buildSearchInput(initialValue, onChange) {
    const wrapper = document.createElement("div");
    wrapper.className = "provider-settings";

    const label = document.createElement("div");
    label.className = "panel-section-title";
    label.textContent = "Search dependencies";
    wrapper.appendChild(label);

    const input = document.createElement("input");
    input.type = "search";
    input.placeholder = "Search dependencies";
    input.className = "input";
    input.value = initialValue;
    input.oninput = () => onChange(input.value || "");
    wrapper.appendChild(input);
    return wrapper;
  }

  function renderDependencies(container, payload) {
    if (!container) return;
    const status = normalizeStatus(payload);
    if (!status) return;
    let search = "";
    const section = document.createElement("div");
    section.className = "provider-settings";

    async function runAction(action, extraBody) {
      const body = { action: action, ...(extraBody || {}) };
      const response = await net.postJson("/api/dependencies", body);
      await refreshDependencies();
      const latest = normalizeStatus(getCachedDependencies());
      if (latest) {
        draw(latest);
      }
      return response;
    }

    function draw(currentStatus) {
      section.innerHTML = "";
      section.appendChild(buildCounts(currentStatus));
      section.appendChild(buildSearchInput(search, (value) => {
        search = value;
        draw(currentStatus);
      }));
      section.appendChild(buildRuntimeDependencies(currentStatus, search, runAction));
      section.appendChild(buildTree(currentStatus, search));
      section.appendChild(buildActions(runAction));
    }

    draw(status);
    container.appendChild(section);
  }

  async function refreshDependencies() {
    const payload = await net.fetchJson("/api/dependencies");
    cachedPayload = payload;
    return payload;
  }

  function getCachedDependencies() {
    return cachedPayload;
  }

  dependencySetup.renderDependencies = renderDependencies;
  dependencySetup.refreshDependencies = refreshDependencies;
  dependencySetup.getCachedDependencies = getCachedDependencies;
})();
