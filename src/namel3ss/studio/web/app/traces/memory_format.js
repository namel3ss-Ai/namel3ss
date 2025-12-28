(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});

  function formatTeamSummaryText(summary) {
    const lines = [];
    if (summary.title) lines.push(summary.title);
    const detail = Array.isArray(summary.lines) ? summary.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }
  function formatExplanationText(explainEvent) {
    const lines = [];
    if (explainEvent.title) lines.push(explainEvent.title);
    const detail = Array.isArray(explainEvent.lines) ? explainEvent.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }
  function formatLinksText(linkEvents) {
    const lines = [];
    linkEvents.forEach((event) => {
      if (event.memory_id) {
        lines.push(`Memory id is ${event.memory_id}.`);
      }
      const detail = Array.isArray(event.lines) ? event.lines : [];
      detail.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    return lines.join("\n");
  }
  function formatPathText(pathEvents) {
    const lines = [];
    pathEvents.forEach((event) => {
      if (event.title) lines.push(event.title);
      if (event.memory_id) {
        lines.push(`Memory id is ${event.memory_id}.`);
      }
      const detail = Array.isArray(event.lines) ? event.lines : [];
      detail.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    return lines.join("\n");
  }
  function formatImpactText(impactEvents) {
    const lines = [];
    impactEvents.forEach((event) => {
      if (event.title) lines.push(event.title);
      if (event.memory_id) {
        lines.push(`Memory id is ${event.memory_id}.`);
      }
      const detail = Array.isArray(event.lines) ? event.lines : [];
      detail.forEach((line) => {
        if (line) lines.push(line);
      });
      const pathDetail = Array.isArray(event.path_lines) ? event.path_lines : [];
      pathDetail.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    return lines.join("\n");
  }

  traces.formatTeamSummaryText = formatTeamSummaryText;
  traces.formatExplanationText = formatExplanationText;
  traces.formatLinksText = formatLinksText;
  traces.formatPathText = formatPathText;
  traces.formatImpactText = formatImpactText;
})();
