(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const net = root.net || (root.net = {});

  async function fetchJson(path, options) {
    const response = await fetch(path, options);
    return response.json();
  }

  async function postJson(path, body) {
    return fetchJson(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
  }

  net.fetchJson = fetchJson;
  net.postJson = postJson;
})();
