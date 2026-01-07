(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const actionResult = root.actionResult || (root.actionResult = {});

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
  }

  actionResult.applyActionResult = applyActionResult;
})();
