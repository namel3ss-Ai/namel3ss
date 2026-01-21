(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const net = root.net;
  const actionResult = root.actionResult || (root.actionResult = {});

  function refreshObservability() {
    if (!net || typeof net.fetchJson !== "function") return;
    net.fetchJson("/api/logs")
      .then((payload) => {
        const entries = payload && Array.isArray(payload.logs) ? payload.logs : [];
        if (state && typeof state.setCachedLogs === "function") {
          state.setCachedLogs(entries);
        }
        if (typeof window.renderLogs === "function") {
          window.renderLogs(entries);
        } else if (root.logs && typeof root.logs.renderLogs === "function") {
          root.logs.renderLogs(entries);
        }
      })
      .catch(() => {});
    net.fetchJson("/api/trace")
      .then((payload) => {
        const spans = payload && Array.isArray(payload.spans) ? payload.spans : [];
        if (state && typeof state.setCachedSpans === "function") {
          state.setCachedSpans(spans);
        }
        if (typeof window.renderTracing === "function") {
          window.renderTracing(spans);
        } else if (root.tracing && typeof root.tracing.renderTracing === "function") {
          root.tracing.renderTracing(spans);
        }
      })
      .catch(() => {});
    net.fetchJson("/api/metrics")
      .then((payload) => {
        if (state && typeof state.setCachedMetrics === "function") {
          state.setCachedMetrics(payload);
        }
        if (typeof window.renderMetrics === "function") {
          window.renderMetrics(payload);
        } else if (root.metrics && typeof root.metrics.renderMetrics === "function") {
          root.metrics.renderMetrics(payload);
        }
      })
      .catch(() => {});
  }

  function applyActionResult(result) {
    const hasTraces = result && Array.isArray(result.traces);
    if (hasTraces) {
      if (state && typeof state.setCachedTraces === "function") {
        state.setCachedTraces(result.traces);
      }
      if (typeof window.renderTraces === "function") {
        window.renderTraces(result.traces);
      } else if (root.traces && typeof root.traces.renderTraces === "function") {
        root.traces.renderTraces(result.traces);
      }
      if (typeof window.renderExplain === "function") {
        window.renderExplain(result.traces);
      } else if (root.explain && typeof root.explain.renderExplain === "function") {
        root.explain.renderExplain(result.traces);
      }
      if (typeof window.renderMemory === "function") {
        window.renderMemory(result.traces);
      } else if (root.memory && typeof root.memory.renderMemory === "function") {
        root.memory.renderMemory(result.traces);
      }
      if (root.errors && typeof root.errors.renderErrors === "function") {
        root.errors.renderErrors(result.traces);
      }
    }

    if (state && typeof state.setCachedLastRunError === "function") {
      if (result && result.ok === false) {
        state.setCachedLastRunError(result);
        if (root.errors && typeof root.errors.renderErrors === "function") {
          root.errors.renderErrors(hasTraces ? result.traces : undefined);
        }
      } else {
        const current = state.getCachedLastRunError ? state.getCachedLastRunError() : null;
        if (current && current.kind === "manifest") {
          return;
        }
        state.setCachedLastRunError(null);
      }
    }
    refreshObservability();
  }

  actionResult.applyActionResult = applyActionResult;
})();
