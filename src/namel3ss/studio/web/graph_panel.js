(() => {
const root = window.N3Studio || {};
const fetchJson = (root.net && root.net.fetchJson) || ((path) => fetch(path).then((res) => res.json()));
let cachedGraph = null;
let selectedGraphNodeId = null;

function setupGraphPanel() {
  const refreshButton = document.getElementById("graphRefresh");
  if (refreshButton) {
    refreshButton.onclick = () => refreshGraphPanel();
  }
}

async function refreshGraphPanel() {
  const canvas = document.getElementById("graphCanvas");
  const details = document.getElementById("graphDetails");
  if (!canvas || !details) return;
  canvas.innerHTML = "";
  details.innerHTML = "";
  showStatus(details, "Loading graph…", "loading");
  try {
    const payload = await fetchJson("/api/graph");
    cachedGraph = payload;
    renderGraph(payload);
  } catch (err) {
    showStatus(details, "Unable to load graph.", "error");
  }
}

function renderGraph(payload) {
  const canvas = document.getElementById("graphCanvas");
  const details = document.getElementById("graphDetails");
  if (!canvas || !details) return;
  canvas.innerHTML = "";
  details.innerHTML = "";

  if (!payload || payload.ok === false) {
    showStatus(details, payload && payload.error ? payload.error : "Unable to load graph.", "error");
    return;
  }
  const nodes = Array.isArray(payload.nodes) ? payload.nodes : [];
  const edges = Array.isArray(payload.edges) ? payload.edges : [];
  if (!nodes.length) {
    showEmpty(canvas, "No graph nodes.");
    showEmpty(details, "Select a node to inspect.");
    return;
  }

  const layout = layoutGraph(nodes);
  applyGraphLayout(canvas, nodes, layout);
  renderGraphEdges(canvas, edges, layout.positions, layout.canvasSize, layout.nodeSize);

  const defaultNode = nodes.find((n) => n.id === selectedGraphNodeId) || nodes[0];
  selectedGraphNodeId = defaultNode.id;
  highlightNode(canvas, selectedGraphNodeId);
  renderGraphDetails(defaultNode);
}

function layoutGraph(nodes) {
  const columns = ["app", "capsule", "package"];
  const groups = { app: [], capsule: [], package: [] };
  nodes.forEach((node) => {
    const type = columns.includes(node.type) ? node.type : "capsule";
    groups[type].push(node);
  });
  const usedColumns = columns.filter((key) => groups[key].length);
  const nodeSize = { width: 180, height: 52 };
  const margin = { x: 24, y: 24 };
  const gap = { x: 220, y: 24 };
  const positions = {};
  let maxHeight = margin.y;
  usedColumns.forEach((key, idx) => {
    const x = margin.x + idx * gap.x;
    let y = margin.y;
    groups[key].forEach((node) => {
      positions[node.id] = { x, y };
      y += nodeSize.height + gap.y;
    });
    maxHeight = Math.max(maxHeight, y);
  });
  const canvasSize = {
    width: margin.x * 2 + Math.max(1, usedColumns.length) * gap.x,
    height: Math.max(maxHeight + margin.y, 320),
  };
  return { positions, canvasSize, nodeSize };
}

function applyGraphLayout(canvas, nodes, layout) {
  canvas.style.width = `${layout.canvasSize.width}px`;
  canvas.style.height = `${layout.canvasSize.height}px`;
  nodes.forEach((node) => {
    const pos = layout.positions[node.id];
    if (!pos) return;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "graph-node";
    button.style.left = `${pos.x}px`;
    button.style.top = `${pos.y}px`;
    button.dataset.nodeId = node.id;
    const version = node.type === "package" && node.version ? `v${node.version}` : "";
    button.innerHTML = `<small>${node.type}</small>${node.name}${version ? ` <span class=\"empty-hint\">${version}</span>` : ""}`;
    button.onclick = () => {
      selectedGraphNodeId = node.id;
      highlightNode(canvas, node.id);
      renderGraphDetails(node);
    };
    canvas.appendChild(button);
  });
}

function renderGraphEdges(canvas, edges, positions, canvasSize, nodeSize) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", `0 0 ${canvasSize.width} ${canvasSize.height}`);
  svg.setAttribute("aria-hidden", "true");
  edges.forEach((edge) => {
    const from = positions[edge.from];
    const to = positions[edge.to];
    if (!from || !to) return;
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.setAttribute("class", "graph-edge");
    line.setAttribute("x1", `${from.x + nodeSize.width}`);
    line.setAttribute("y1", `${from.y + nodeSize.height / 2}`);
    line.setAttribute("x2", `${to.x}`);
    line.setAttribute("y2", `${to.y + nodeSize.height / 2}`);
    svg.appendChild(line);
  });
  canvas.appendChild(svg);
}

function highlightNode(canvas, nodeId) {
  const nodes = Array.from(canvas.querySelectorAll(".graph-node"));
  nodes.forEach((node) => node.classList.toggle("selected", node.dataset.nodeId === nodeId));
}

function renderGraphDetails(node) {
  const details = document.getElementById("graphDetails");
  if (!details) return;
  details.innerHTML = "";
  if (!node) {
    showEmpty(details, "Select a node to inspect.");
    return;
  }
  const section = document.createElement("div");
  section.className = "panel-section";
  section.innerHTML = `<div class=\"panel-section-title\">Details</div>`;
  details.appendChild(section);

  const kv = document.createElement("div");
  kv.className = "key-values";
  kv.innerHTML = `
    <div class=\"kv-row\"><div class=\"kv-label\">name</div><div class=\"kv-value\">${node.name}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">type</div><div class=\"kv-value\">${node.type}</div></div>
    <div class=\"kv-row\"><div class=\"kv-label\">source</div><div class=\"kv-value\">${node.source || "n/a"}</div></div>
  `;
  if (node.type === "package") {
    kv.innerHTML += `
      <div class=\"kv-row\"><div class=\"kv-label\">version</div><div class=\"kv-value\">${node.version || "n/a"}</div></div>
      <div class=\"kv-row\"><div class=\"kv-label\">license</div><div class=\"kv-value\">${node.license || "n/a"}</div></div>
    `;
  }
  details.appendChild(kv);

  const exports = node.exports || {};
  const exportKinds = Object.keys(exports || {}).sort();
  if (!exportKinds.length) {
    const empty = document.createElement("div");
    empty.className = "empty-hint";
    empty.textContent = "No exports.";
    details.appendChild(empty);
    return;
  }
  const exportsBlock = document.createElement("div");
  exportsBlock.className = "panel-stack";
  exportKinds.forEach((kind) => {
    const items = exports[kind] || [];
    const row = document.createElement("div");
    row.innerHTML = `<strong>${kind}</strong>: ${items.join(", ") || "n/a"}`;
    exportsBlock.appendChild(row);
  });
  details.appendChild(exportsBlock);
}

function showStatus(container, message, kind) {
  container.innerHTML = "";
  const banner = document.createElement("div");
  banner.className = `status-banner ${kind || ""}`.trim();
  banner.textContent = message;
  container.appendChild(banner);
}

setupGraphPanel();
window.refreshGraphPanel = refreshGraphPanel;
})();
