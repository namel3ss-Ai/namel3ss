from __future__ import annotations


DOCS_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>namel3ss docs</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f8f5f0;
      --panel: #ffffff;
      --ink: #1c1b19;
      --accent: #2a6f97;
      --muted: #6b6a68;
      --border: #e3ddd4;
      --shadow: rgba(22, 20, 16, 0.08);
    }
    body {
      margin: 0;
      font-family: "Garamond", "Palatino Linotype", "Book Antiqua", serif;
      background: radial-gradient(circle at top left, #fff7e6, #f0efe9 40%, #f8f5f0);
      color: var(--ink);
    }
    header {
      padding: 32px 24px 16px;
      border-bottom: 1px solid var(--border);
    }
    header h1 {
      margin: 0;
      font-size: 28px;
      letter-spacing: 0.5px;
    }
    header p {
      margin: 6px 0 0;
      color: var(--muted);
    }
    main {
      display: grid;
      grid-template-columns: minmax(260px, 1fr) minmax(300px, 1.2fr);
      gap: 20px;
      padding: 20px 24px 32px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 10px 30px var(--shadow);
      padding: 16px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 20px;
    }
    h3 {
      margin: 16px 0 8px;
      font-size: 16px;
      color: var(--accent);
    }
    pre {
      background: #f6f1e7;
      padding: 12px;
      border-radius: 8px;
      font-size: 13px;
      overflow-x: auto;
    }
    .endpoint {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px dashed var(--border);
    }
    .endpoint:last-child {
      border-bottom: none;
    }
    .badge {
      font-weight: 700;
      color: var(--accent);
    }
    label {
      display: block;
      margin-top: 10px;
      font-size: 13px;
      color: var(--muted);
    }
    input, textarea, select, button {
      width: 100%;
      padding: 8px;
      margin-top: 4px;
      border-radius: 8px;
      border: 1px solid var(--border);
      font-family: inherit;
      font-size: 14px;
    }
    button {
      background: var(--accent);
      color: white;
      cursor: pointer;
      border: none;
      margin-top: 12px;
    }
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .small {
      font-size: 12px;
      color: var(--muted);
    }
    @media (max-width: 900px) {
      main {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>namel3ss API docs</h1>
    <p>Generated from your routes and AI flows. Updates every few seconds.</p>
  </header>
  <main>
    <section>
      <h2>Endpoints</h2>
      <div id="endpoints"></div>
    </section>
    <section>
      <h2>Try it</h2>
      <label for="endpointSelect">Endpoint</label>
      <select id="endpointSelect"></select>
      <div class="two-col">
        <div>
          <label for="pathParams">Path params (JSON)</label>
          <textarea id="pathParams" rows="4">{}</textarea>
        </div>
        <div>
          <label for="queryParams">Query params (JSON)</label>
          <textarea id="queryParams" rows="4">{}</textarea>
        </div>
      </div>
      <label for="bodyParams">Body (JSON)</label>
      <textarea id="bodyParams" rows="6">{}</textarea>
      <button id="sendBtn">Send request</button>
      <h3>Response</h3>
      <pre id="responseBox"></pre>
    </section>
  </main>
  <script>
    const state = { spec: null };
    const endpointSelect = document.getElementById("endpointSelect");
    const responseBox = document.getElementById("responseBox");

    async function loadSpec() {
      const res = await fetch("/openapi.json");
      const spec = await res.json();
      if (spec && spec.paths) {
        const specText = JSON.stringify(spec);
        if (!state.spec || state.specText !== specText) {
          state.spec = spec;
          state.specText = specText;
          renderEndpoints(spec);
          renderSelect(spec);
        }
      }
    }

    function renderEndpoints(spec) {
      const container = document.getElementById("endpoints");
      container.innerHTML = "";
      const endpoints = collectEndpoints(spec);
      endpoints.forEach((item) => {
        const row = document.createElement("div");
        row.className = "endpoint";
        row.innerHTML = `<span class="badge">${item.method}</span><span>${item.path}</span>`;
        container.appendChild(row);
      });
    }

    function renderSelect(spec) {
      endpointSelect.innerHTML = "";
      collectEndpoints(spec).forEach((item, idx) => {
        const option = document.createElement("option");
        option.value = idx;
        option.textContent = `${item.method} ${item.path}`;
        endpointSelect.appendChild(option);
      });
    }

    function collectEndpoints(spec) {
      const endpoints = [];
      Object.keys(spec.paths || {}).forEach((path) => {
        const methods = spec.paths[path];
        Object.keys(methods).forEach((method) => {
          endpoints.push({ path, method: method.toUpperCase(), op: methods[method] });
        });
      });
      return endpoints.sort((a, b) => a.path.localeCompare(b.path));
    }

    async function sendRequest() {
      const endpoints = collectEndpoints(state.spec);
      const selected = endpoints[endpointSelect.value];
      if (!selected) return;
      let pathParams = {};
      let queryParams = {};
      let bodyParams = {};
      try { pathParams = JSON.parse(document.getElementById("pathParams").value || "{}"); } catch (e) {}
      try { queryParams = JSON.parse(document.getElementById("queryParams").value || "{}"); } catch (e) {}
      try { bodyParams = JSON.parse(document.getElementById("bodyParams").value || "{}"); } catch (e) {}
      let renderedPath = selected.path.replace(/\\{(\\w+)\\}/g, (_, key) => String(pathParams[key] || ""));
      const url = new URL(renderedPath, window.location.origin);
      Object.entries(queryParams).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
      const options = { method: selected.method, headers: {} };
      if (!["GET", "HEAD"].includes(selected.method)) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(bodyParams || {});
      }
      const res = await fetch(url.toString(), options);
      const json = await res.json().catch(() => ({}));
      responseBox.textContent = JSON.stringify(json, null, 2);
    }

    document.getElementById("sendBtn").addEventListener("click", sendRequest);

    async function refreshAll() {
      await loadSpec();
    }

    refreshAll();
    setInterval(refreshAll, 5000);
  </script>
</body>
</html>
"""


__all__ = ["DOCS_HTML"]
