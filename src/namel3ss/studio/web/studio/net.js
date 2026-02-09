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

  function _runtimeError(category, message, hint, origin, stableCode) {
    return {
      category: category,
      message: message,
      hint: hint,
      origin: origin,
      stable_code: stableCode,
    };
  }

  function _networkRuntimeError(path) {
    return _runtimeError(
      "server_unavailable",
      "Runtime server is unavailable.",
      `Start the runtime server and retry ${path}.`,
      "network",
      "runtime.server_unavailable"
    );
  }

  function _errorWithRuntime(error, runtimeError, status, payload) {
    const message = (runtimeError && runtimeError.message) || (error && error.message) || "Request failed";
    const wrapped = new Error(message);
    wrapped.runtime_error = runtimeError;
    if (Number.isInteger(status)) wrapped.status = status;
    if (payload && typeof payload === "object") wrapped.payload = payload;
    return wrapped;
  }

  async function fetchJson(path, options) {
    let response;
    try {
      response = await fetch(path, options);
    } catch (err) {
      throw _errorWithRuntime(err, _networkRuntimeError(path));
    }
    let payload = null;
    try {
      payload = await response.json();
    } catch (_err) {
      payload = null;
    }
    if (payload && typeof payload === "object") {
      return payload;
    }
    if (response.ok) return {};
    const runtimeError = _runtimeError(
      response.status === 401 || response.status === 403 ? "auth_invalid" : "runtime_internal",
      `Request failed with status ${response.status}.`,
      "Check server logs and retry the request.",
      "runtime",
      `runtime.http_${response.status}`
    );
    throw _errorWithRuntime(null, runtimeError, response.status, payload);
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
    let response;
    try {
      response = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(body || {}),
        signal: opts.signal || undefined,
      });
    } catch (err) {
      throw _errorWithRuntime(err, _networkRuntimeError(path));
    }
    if (!response.ok) {
      const text = await response.text();
      const parsed = _safeJsonParse(text);
      if (parsed && typeof parsed === "object" && parsed.runtime_error) {
        throw _errorWithRuntime(null, parsed.runtime_error, response.status, parsed);
      }
      const runtimeError = _runtimeError(
        response.status === 401 || response.status === 403 ? "auth_invalid" : "runtime_internal",
        text || `Request failed with status ${response.status}`,
        "Check server logs and retry the request.",
        "runtime",
        `runtime.http_${response.status}`
      );
      throw _errorWithRuntime(null, runtimeError, response.status, parsed);
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
