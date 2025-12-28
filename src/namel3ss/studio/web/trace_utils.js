function updateTraceCopyButtons() {
  const outputBtn = document.getElementById("traceCopyOutput");
  const jsonBtn = document.getElementById("traceCopyJson");
  const has = !!selectedTrace;
  [outputBtn, jsonBtn].forEach((btn) => {
    if (!btn) return;
    btn.disabled = !has;
  });
  if (outputBtn) {
    outputBtn.onclick = () => {
      if (selectedTrace) copyText(selectedTrace.output ?? selectedTrace.result ?? "");
    };
  }
  if (jsonBtn) {
    jsonBtn.onclick = () => {
      if (selectedTrace) copyText(selectedTrace);
    };
  }
}

function formatPlainTrace(value) {
  const lines = [];
  flattenPlainTrace(lines, "", value);
  return lines.join("\n");
}

function flattenPlainTrace(lines, prefix, value) {
  if (Array.isArray(value)) {
    const countKey = prefix ? `${prefix}.count` : "count";
    lines.push(`${countKey}: ${value.length}`);
    value.forEach((item, index) => {
      const itemPrefix = prefix ? `${prefix}.${index + 1}` : `${index + 1}`;
      flattenPlainTrace(lines, itemPrefix, item);
    });
    return;
  }
  if (value && typeof value === "object") {
    const keys = Object.keys(value).sort();
    keys.forEach((key) => {
      const nextPrefix = prefix ? `${prefix}.${key}` : key;
      flattenPlainTrace(lines, nextPrefix, value[key]);
    });
    return;
  }
  const formatted = formatPlainScalar(value);
  const key = prefix || "value";
  lines.push(`${key}: ${formatted}`);
}

function formatPlainScalar(value) {
  if (value === null || value === undefined) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  return sanitizePlainText(String(value));
}

function sanitizePlainText(text) {
  return text.replace(/\r/g, "\\r").replace(/\n/g, "\\n").replace(/\t/g, "\\t");
}
