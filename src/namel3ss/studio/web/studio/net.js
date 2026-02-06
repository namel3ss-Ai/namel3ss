(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const net = root.net || (root.net = {});

  function _safeJsonParse(text) {
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch (err) {
      return null;
    }
  }

  function _parseSseFrame(frame) {
    const lines = String(frame || "").split("\n");
    let event = "message";
    const dataLines = [];
    for (const line of lines) {
      if (!line) continue;
      if (line.startsWith("event:")) {
        event = line.slice(6).trim() || "message";
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trimStart());
      }
    }
    return { event, data: _safeJsonParse(dataLines.join("\n")) };
  }

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

  async function postSse(path, body, options) {
    const opts = options || {};
    const onEvent = typeof opts.onEvent === "function" ? opts.onEvent : null;
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body || {}),
      signal: opts.signal || undefined,
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Request failed with status ${response.status}`);
    }
    if (!response.body) {
      const text = await response.text();
      let finalPayload = {};
      for (const frame of String(text || "").split("\n\n")) {
        if (!frame.trim()) continue;
        const parsed = _parseSseFrame(frame);
        if (parsed.event === "return" && parsed.data && typeof parsed.data === "object") {
          finalPayload = parsed.data;
        } else if (onEvent) {
          onEvent(parsed);
        }
      }
      return finalPayload;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalPayload = {};

    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      let splitAt = buffer.indexOf("\n\n");
      while (splitAt >= 0) {
        const frame = buffer.slice(0, splitAt);
        buffer = buffer.slice(splitAt + 2);
        const parsed = _parseSseFrame(frame);
        if (parsed.event === "return") {
          if (parsed.data && typeof parsed.data === "object") {
            finalPayload = parsed.data;
          }
        } else if (onEvent) {
          onEvent(parsed);
        }
        splitAt = buffer.indexOf("\n\n");
      }
    }

    if (buffer.trim()) {
      const parsed = _parseSseFrame(buffer);
      if (parsed.event === "return" && parsed.data && typeof parsed.data === "object") {
        finalPayload = parsed.data;
      } else if (onEvent) {
        onEvent(parsed);
      }
    }
    return finalPayload;
  }

  net.fetchJson = fetchJson;
  net.postJson = postJson;
  net.postSse = postSse;
})();
