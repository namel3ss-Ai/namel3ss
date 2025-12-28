(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});
  const utils = root.utils;
  function renderPlainTraceValue(value) {
    if (Array.isArray(value) || (value && typeof value === "object")) {
      return formatPlainTrace(value);
    }
    return formatPlainScalar(value);
  }
  function appendTraceSection(details, label, value, copyable = false, renderMode = "json") {
    if (value === undefined || value === null || (typeof value === "object" && Object.keys(value).length === 0)) {
      return;
    }
    const wrapper = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = label;
    if (copyable) {
      const copyBtn = document.createElement("button");
      copyBtn.className = "btn ghost small";
      copyBtn.textContent = "Copy";
      copyBtn.onclick = () => window.copyText(value);
      heading.appendChild(copyBtn);
    }
    wrapper.appendChild(heading);
    const content = renderMode === "plain" ? renderPlainTraceValue(value) : value;
    wrapper.appendChild(utils.createCodeBlock(content));
    details.appendChild(wrapper);
  }
  traces.renderPlainTraceValue = renderPlainTraceValue;
  traces.appendTraceSection = appendTraceSection;
})();
