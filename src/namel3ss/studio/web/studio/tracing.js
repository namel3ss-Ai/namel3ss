(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const tracing = root.tracing || (root.tracing = {});

  function getContainer() {
    return document.getElementById("tracing");
  }

  function buildTree(spans) {
    const nodes = new Map();
    spans.forEach((span) => {
      if (!span || typeof span !== "object") return;
      nodes.set(span.id, { span, children: [] });
    });
    const roots = [];
    spans.forEach((span) => {
      if (!span || typeof span !== "object") return;
      const node = nodes.get(span.id);
      const parentId = span.parent_id;
      if (parentId && nodes.has(parentId)) {
        nodes.get(parentId).children.push(node);
      } else {
        roots.push(node);
      }
    });
    return roots;
  }

  function buildHeader(span, depth) {
    const header = document.createElement("div");
    header.className = "span-header";
    header.style.paddingLeft = `${depth * 16}px`;

    const name = document.createElement("div");
    name.className = "span-name";
    name.textContent = span.name || span.kind || "span";

    const kind = document.createElement("div");
    kind.className = "span-kind";
    kind.textContent = span.kind || "";

    const meta = document.createElement("div");
    meta.className = "span-meta";
    const duration = typeof span.duration_steps === "number" ? `${span.duration_steps} steps` : "";
    const range = span.start_step !== undefined && span.end_step !== undefined
      ? `step ${span.start_step} -> ${span.end_step}`
      : "";
    meta.textContent = [range, duration].filter(Boolean).join(" | ");

    const status = document.createElement("div");
    status.className = "span-status";
    status.textContent = span.status || "";

    header.appendChild(name);
    if (kind.textContent) header.appendChild(kind);
    if (meta.textContent) header.appendChild(meta);
    if (status.textContent) header.appendChild(status);
    return header;
  }

  function buildDetails(span) {
    const details = span.details && typeof span.details === "object" ? span.details : null;
    if (!details || !Object.keys(details).length) return null;
    const wrapper = document.createElement("details");
    wrapper.className = "span-details";

    const summary = document.createElement("summary");
    summary.textContent = "Details";
    wrapper.appendChild(summary);

    const body = document.createElement("pre");
    body.textContent = JSON.stringify(details, null, 2);
    wrapper.appendChild(body);
    return wrapper;
  }

  function renderNode(node, depth) {
    const span = node.span;
    const row = document.createElement("div");
    const status = span.status || "ok";
    row.className = `span-row span-status-${status}`;
    row.appendChild(buildHeader(span, depth));
    const details = buildDetails(span);
    if (details) row.appendChild(details);
    node.children.forEach((child) => {
      row.appendChild(renderNode(child, depth + 1));
    });
    return row;
  }

  function renderTracing(input) {
    const container = getContainer();
    if (!container) return;
    const list = Array.isArray(input)
      ? input
      : (state && typeof state.getCachedSpans === "function" ? state.getCachedSpans() : []);
    const spans = Array.isArray(list) ? list : [];
    if (!spans.length) {
      dom.showEmpty(container, "No spans yet. Run your app.");
      return;
    }
    container.innerHTML = "";
    const roots = buildTree(spans);
    roots.forEach((node) => {
      container.appendChild(renderNode(node, 0));
    });
  }

  async function refreshTracing() {
    if (!net || typeof net.fetchJson !== "function") return;
    try {
      const payload = await net.fetchJson("/api/traces");
      const spans = payload && Array.isArray(payload.spans) ? payload.spans : [];
      if (state && typeof state.setCachedSpans === "function") {
        state.setCachedSpans(spans);
      }
      renderTracing(spans);
    } catch (_err) {
      renderTracing([]);
    }
  }

  tracing.renderTracing = renderTracing;
  tracing.refreshTracing = refreshTracing;
  window.renderTracing = renderTracing;
})();
