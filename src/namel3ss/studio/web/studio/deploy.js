(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const guidance = root.guidance || {};
  const deploy = root.deploy || (root.deploy = {});

  function buildBadge(text, kind) {
    const badge = document.createElement("span");
    badge.className = `deploy-badge ${kind ? `status-${kind}` : ""}`.trim();
    badge.textContent = text;
    return badge;
  }

  function formatSlot(slot) {
    if (!slot || (!slot.target && !slot.build_id)) return "none";
    const target = slot.target || "unknown";
    const build = slot.build_id || "unknown";
    return `${target} / ${build}`;
  }

  function buildSummaryRow(label, value) {
    const row = document.createElement("div");
    row.className = "deploy-row";
    const name = document.createElement("div");
    name.className = "deploy-row-label";
    name.textContent = label;
    const val = document.createElement("div");
    val.className = "deploy-row-value";
    val.textContent = value || "none";
    row.appendChild(name);
    row.appendChild(val);
    return row;
  }

  function buildGuidanceCard(text) {
    const parsed = guidance.parseGuidance ? guidance.parseGuidance(text) : { raw: String(text || "") };
    const card = document.createElement("div");
    card.className = "deploy-guidance-card";
    const title = document.createElement("div");
    title.className = "deploy-guidance-title";
    title.textContent = parsed.what || "Guidance";
    card.appendChild(title);
    const body = document.createElement("div");
    body.className = "deploy-guidance-body";
    const rows = [
      ["Why", parsed.why],
      ["Fix", parsed.fix],
      ["Example", parsed.example],
    ].filter((entry) => entry[1]);
    if (!rows.length && parsed.raw) {
      rows.push(["Details", parsed.raw]);
    }
    rows.forEach(([label, value]) => {
      const row = document.createElement("div");
      row.className = "deploy-guidance-row";
      const key = document.createElement("div");
      key.className = "deploy-guidance-key";
      key.textContent = label;
      const val = document.createElement("div");
      val.className = "deploy-guidance-value";
      val.textContent = value;
      row.appendChild(key);
      row.appendChild(val);
      body.appendChild(row);
    });
    card.appendChild(body);
    return card;
  }

  function buildEntryDetail(entry) {
    if (entry.secret_name) return `Secret ${entry.secret_name}`;
    if (entry.reason) return entry.reason;
    if (entry.purpose) return entry.purpose;
    return "";
  }

  function renderDeploymentCard(card, payload) {
    card.innerHTML = "";
    const header = document.createElement("div");
    header.className = "deploy-card-header";
    const title = document.createElement("div");
    title.className = "deploy-card-title";
    title.textContent = "Deployment";
    const status = buildBadge(`status ${payload.status || "unknown"}`, payload.status || "unknown");
    header.appendChild(title);
    header.appendChild(status);
    card.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "deploy-grid";
    grid.appendChild(buildSummaryRow("Active", formatSlot(payload.active)));
    grid.appendChild(buildSummaryRow("Last ship", formatSlot(payload.last_ship)));
    grid.appendChild(buildSummaryRow("Previous", formatSlot(payload.previous)));
    grid.appendChild(buildSummaryRow("Rollback", payload.rollback_available ? "available" : "none"));
    if (payload.active_build && payload.active_build.location) {
      grid.appendChild(buildSummaryRow("Active location", payload.active_build.location));
    }
    card.appendChild(grid);

    const guidanceItems = []
      .concat(Array.isArray(payload.guidance) ? payload.guidance : [])
      .concat(payload.environment && Array.isArray(payload.environment.guidance) ? payload.environment.guidance : []);
    if (guidanceItems.length) {
      const guidanceWrap = document.createElement("div");
      guidanceWrap.className = "deploy-guidance";
      const heading = document.createElement("div");
      heading.className = "deploy-section-title";
      heading.textContent = "Guidance";
      guidanceWrap.appendChild(heading);
      guidanceItems.forEach((item) => {
        if (item) guidanceWrap.appendChild(buildGuidanceCard(String(item)));
      });
      card.appendChild(guidanceWrap);
    }
  }

  function renderBuildsCard(card, payload) {
    card.innerHTML = "";
    const header = document.createElement("div");
    header.className = "deploy-card-header";
    const title = document.createElement("div");
    title.className = "deploy-card-title";
    title.textContent = "Builds";
    header.appendChild(title);
    card.appendChild(header);

    const builds = Array.isArray(payload.builds) ? payload.builds : [];
    if (!builds.length) {
      card.appendChild(dom.buildEmpty("No builds recorded."));
      return;
    }
    const list = document.createElement("div");
    list.className = "deploy-list";
    builds.forEach((build) => {
      const row = document.createElement("div");
      row.className = "deploy-build";
      const rowHeader = document.createElement("div");
      rowHeader.className = "deploy-build-header";
      const name = document.createElement("div");
      name.className = "deploy-build-name";
      name.textContent = build.target || "target";
      const badge = buildBadge(build.status || "missing", build.status || "missing");
      rowHeader.appendChild(name);
      rowHeader.appendChild(badge);
      row.appendChild(rowHeader);

      const meta = document.createElement("div");
      meta.className = "deploy-build-meta";
      const buildId = build.build_id || "none";
      const parts = [`Build ${buildId}`];
      if (build.location) parts.push(build.location);
      meta.textContent = parts.join(" · ");
      row.appendChild(meta);

      const instructions = build.entry_instructions && typeof build.entry_instructions === "object"
        ? build.entry_instructions
        : null;
      if (instructions) {
        const instructionList = document.createElement("div");
        instructionList.className = "deploy-instructions";
        Object.keys(instructions).sort().forEach((key) => {
          const line = document.createElement("div");
          line.className = "deploy-instruction";
          line.textContent = `${key}: ${instructions[key]}`;
          instructionList.appendChild(line);
        });
        row.appendChild(instructionList);
      }
      list.appendChild(row);
    });
    card.appendChild(list);
  }

  function renderEnvironmentCard(card, payload) {
    card.innerHTML = "";
    const header = document.createElement("div");
    header.className = "deploy-card-header";
    const title = document.createElement("div");
    title.className = "deploy-card-title";
    title.textContent = "Environment";
    header.appendChild(title);
    card.appendChild(header);

    if (!payload || payload.ok === false) {
      card.appendChild(dom.buildEmpty("Environment summary unavailable."));
      return;
    }

    const summary = payload.summary || {};
    const summaryLine = document.createElement("div");
    summaryLine.className = "deploy-meta";
    summaryLine.textContent = `Required ${summary.required || 0} (missing ${summary.missing || 0}) · Optional ${
      summary.optional || 0
    } · Overrides ${summary.overrides || 0}`;
    card.appendChild(summaryLine);

    const sources = Array.isArray(payload.sources) ? payload.sources : [];
    if (sources.length) {
      const sourceLine = document.createElement("div");
      sourceLine.className = "deploy-meta";
      sourceLine.textContent = `Sources: ${sources.map((item) => item.kind).filter(Boolean).join(", ")}`;
      card.appendChild(sourceLine);
    }

    const required = Array.isArray(payload.required) ? payload.required : [];
    if (required.length) {
      const heading = document.createElement("div");
      heading.className = "deploy-section-title";
      heading.textContent = "Required";
      card.appendChild(heading);
      const list = document.createElement("div");
      list.className = "deploy-entry-list";
      required.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "deploy-entry";
        const title = document.createElement("div");
        title.className = "deploy-entry-title";
        title.textContent = entry.name || "required";
        const detail = document.createElement("div");
        detail.className = "deploy-entry-detail";
        detail.textContent = buildEntryDetail(entry);
        const left = document.createElement("div");
        left.className = "deploy-entry-left";
        left.appendChild(title);
        if (detail.textContent) left.appendChild(detail);
        const right = document.createElement("div");
        right.className = "deploy-entry-right";
        right.appendChild(buildBadge(entry.status || "missing", entry.status || "missing"));
        const source = document.createElement("div");
        source.className = "deploy-entry-source";
        source.textContent = entry.source || "missing";
        right.appendChild(source);
        row.appendChild(left);
        row.appendChild(right);
        list.appendChild(row);
      });
      card.appendChild(list);
    }

    const optional = Array.isArray(payload.optional) ? payload.optional : [];
    if (optional.length) {
      const heading = document.createElement("div");
      heading.className = "deploy-section-title";
      heading.textContent = "Optional";
      card.appendChild(heading);
      const list = document.createElement("div");
      list.className = "deploy-entry-list";
      optional.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "deploy-entry";
        const title = document.createElement("div");
        title.className = "deploy-entry-title";
        title.textContent = entry.name || "optional";
        const detail = document.createElement("div");
        detail.className = "deploy-entry-detail";
        detail.textContent = buildEntryDetail(entry);
        const left = document.createElement("div");
        left.className = "deploy-entry-left";
        left.appendChild(title);
        if (detail.textContent) left.appendChild(detail);
        const right = document.createElement("div");
        right.className = "deploy-entry-right";
        right.appendChild(buildBadge(entry.status || "unset", entry.status || "unset"));
        const source = document.createElement("div");
        source.className = "deploy-entry-source";
        source.textContent = entry.source || "missing";
        right.appendChild(source);
        row.appendChild(left);
        row.appendChild(right);
        list.appendChild(row);
      });
      card.appendChild(list);
    }

    if (Array.isArray(payload.overrides) && payload.overrides.length) {
      const heading = document.createElement("div");
      heading.className = "deploy-section-title";
      heading.textContent = "Overrides";
      card.appendChild(heading);
      const list = document.createElement("div");
      list.className = "deploy-overrides";
      payload.overrides.forEach((item) => {
        const chip = document.createElement("span");
        chip.className = "deploy-chip";
        chip.textContent = item;
        list.appendChild(chip);
      });
      card.appendChild(list);
    }
  }

  async function renderDeploy() {
    const panel = document.getElementById("deploy");
    if (!panel) return;
    panel.innerHTML = "";
    const wrapper = document.createElement("div");
    wrapper.className = "deploy-panel";
    panel.appendChild(wrapper);

    const header = document.createElement("div");
    header.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Deploy";
    const meta = document.createElement("div");
    meta.className = "deploy-meta";
    meta.textContent = "Loading deployment data...";
    header.appendChild(title);
    header.appendChild(meta);
    wrapper.appendChild(header);

    const deployCard = document.createElement("div");
    deployCard.className = "list-item deploy-card";
    const buildsCard = document.createElement("div");
    buildsCard.className = "list-item deploy-card";
    const envCard = document.createElement("div");
    envCard.className = "list-item deploy-card";
    wrapper.appendChild(deployCard);
    wrapper.appendChild(buildsCard);
    wrapper.appendChild(envCard);

    try {
      const [deployPayload, buildPayload] = await Promise.all([
        net.fetchJson("/api/deploy"),
        net.fetchJson("/api/build"),
      ]);
      if (!deployPayload || deployPayload.ok === false) {
        dom.showError(deployCard, (deployPayload && deployPayload.error) || "Deployment payload unavailable.");
        meta.textContent = "Deploy unavailable";
      } else {
        renderDeploymentCard(deployCard, deployPayload);
        meta.textContent = `Status ${deployPayload.status || "unknown"}`;
      }
      if (!buildPayload || buildPayload.ok === false) {
        dom.showError(buildsCard, (buildPayload && buildPayload.error) || "Build payload unavailable.");
      } else {
        renderBuildsCard(buildsCard, buildPayload);
      }
      renderEnvironmentCard(envCard, deployPayload && deployPayload.environment ? deployPayload.environment : null);
    } catch (err) {
      dom.showError(wrapper, err && err.message ? err.message : String(err || "Unable to load deploy panel."));
      meta.textContent = "Deploy unavailable";
    }
  }

  deploy.renderDeploy = renderDeploy;
  window.renderDeploy = renderDeploy;
})();
