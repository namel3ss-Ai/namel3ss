(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const marketplace = root.marketplace || (root.marketplace = {});

  async function queryMarketplace(query, includePending) {
    return net.postJson("/api/marketplace", {
      action: "search",
      query: query || "",
      include_pending: Boolean(includePending),
    });
  }

  function buildItemCard(item, statusNode) {
    const card = document.createElement("div");
    card.className = "list-item";

    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = `${item.name}@${item.version}`;
    card.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "status-lines";
    [
      `type ${item.type}`,
      `status ${item.status}`,
      `author ${item.author}`,
      `rating ${Number(item.rating_avg || 0).toFixed(2)} (${item.rating_count || 0})`,
      item.description || "",
    ].forEach((line) => {
      if (!line) return;
      const row = document.createElement("div");
      row.className = "status-line";
      row.textContent = line;
      meta.appendChild(row);
    });
    card.appendChild(meta);

    const actions = document.createElement("div");
    actions.className = "ui-buttons";

    const installBtn = document.createElement("button");
    installBtn.className = "btn ghost";
    installBtn.textContent = "Install";
    installBtn.addEventListener("click", async () => {
      installBtn.disabled = true;
      installBtn.textContent = "Installing...";
      try {
        const payload = await net.postJson("/api/marketplace", {
          action: "install",
          name: item.name,
          version: item.version,
        });
        const count = payload && Array.isArray(payload.installed_files) ? payload.installed_files.length : 0;
        statusNode.textContent = `Installed ${count} file(s) from ${item.name}@${item.version}.`;
      } catch (err) {
        statusNode.textContent = err && err.message ? err.message : "Install failed.";
        statusNode.classList.add("error");
      } finally {
        installBtn.disabled = false;
        installBtn.textContent = "Install";
      }
    });
    actions.appendChild(installBtn);

    const ratingInput = document.createElement("input");
    ratingInput.type = "number";
    ratingInput.min = "1";
    ratingInput.max = "5";
    ratingInput.value = "5";
    ratingInput.style.width = "64px";
    actions.appendChild(ratingInput);

    const rateBtn = document.createElement("button");
    rateBtn.className = "btn ghost";
    rateBtn.textContent = "Rate";
    rateBtn.addEventListener("click", async () => {
      try {
        await net.postJson("/api/marketplace", {
          action: "rate",
          name: item.name,
          version: item.version,
          rating: Number(ratingInput.value || 0),
          comment: "",
        });
        statusNode.textContent = `Saved rating for ${item.name}@${item.version}.`;
      } catch (err) {
        statusNode.textContent = err && err.message ? err.message : "Rating failed.";
        statusNode.classList.add("error");
      }
    });
    actions.appendChild(rateBtn);

    const commentsBtn = document.createElement("button");
    commentsBtn.className = "btn ghost";
    commentsBtn.textContent = "Comments";
    commentsBtn.addEventListener("click", async () => {
      try {
        const payload = await net.postJson("/api/marketplace", {
          action: "comments",
          name: item.name,
          version: item.version,
        });
        const count = payload && payload.count ? payload.count : 0;
        statusNode.textContent = `Loaded ${count} comment(s) for ${item.name}@${item.version}.`;
      } catch (err) {
        statusNode.textContent = err && err.message ? err.message : "Comments failed.";
        statusNode.classList.add("error");
      }
    });
    actions.appendChild(commentsBtn);

    card.appendChild(actions);
    return card;
  }

  async function renderMarketplace() {
    const panel = document.getElementById("marketplace");
    if (!panel) return;
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";

    const controls = document.createElement("div");
    controls.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Marketplace";
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Search marketplace items";
    const includePending = document.createElement("input");
    includePending.type = "checkbox";
    const includeLabel = document.createElement("label");
    includeLabel.textContent = "Include pending";
    includeLabel.prepend(includePending);
    const searchBtn = document.createElement("button");
    searchBtn.className = "btn ghost";
    searchBtn.textContent = "Search";
    const publishPath = document.createElement("input");
    publishPath.type = "text";
    publishPath.placeholder = "Publish path (manifest folder)";
    const publishBtn = document.createElement("button");
    publishBtn.className = "btn ghost";
    publishBtn.textContent = "Publish";

    const controlsRow = document.createElement("div");
    controlsRow.className = "ui-buttons";
    controlsRow.appendChild(searchBtn);
    controlsRow.appendChild(includeLabel);

    const publishRow = document.createElement("div");
    publishRow.className = "preview-input";
    publishRow.appendChild(publishPath);
    publishRow.appendChild(publishBtn);

    controls.appendChild(title);
    controls.appendChild(input);
    controls.appendChild(controlsRow);
    controls.appendChild(publishRow);

    const status = document.createElement("div");
    status.className = "preview-hint";
    controls.appendChild(status);

    wrapper.appendChild(controls);

    const list = document.createElement("div");
    list.className = "list";
    wrapper.appendChild(list);
    panel.appendChild(wrapper);

    const refresh = async () => {
      status.textContent = "";
      status.classList.remove("error");
      list.innerHTML = "";
      try {
        const payload = await queryMarketplace(input.value, includePending.checked);
        const items = payload && Array.isArray(payload.items) ? payload.items : [];
        if (!items.length) {
          list.appendChild(dom.buildEmpty("No marketplace items matched."));
          return;
        }
        items.forEach((item) => {
          list.appendChild(buildItemCard(item, status));
        });
      } catch (err) {
        status.textContent = err && err.message ? err.message : "Marketplace search failed.";
        status.classList.add("error");
      }
    };

    searchBtn.addEventListener("click", () => refresh());
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        refresh();
      }
    });

    publishBtn.addEventListener("click", async () => {
      const path = publishPath.value ? publishPath.value.trim() : "";
      if (!path) {
        status.textContent = "Provide a path first.";
        status.classList.add("error");
        return;
      }
      publishBtn.disabled = true;
      publishBtn.textContent = "Publishing...";
      try {
        const payload = await net.postJson("/api/marketplace", { action: "publish", path });
        status.textContent = `Published ${payload.name}@${payload.version} as ${payload.status}.`;
        status.classList.remove("error");
        refresh();
      } catch (err) {
        status.textContent = err && err.message ? err.message : "Publish failed.";
        status.classList.add("error");
      } finally {
        publishBtn.disabled = false;
        publishBtn.textContent = "Publish";
      }
    });

    refresh();
  }

  marketplace.renderMarketplace = renderMarketplace;
})();
