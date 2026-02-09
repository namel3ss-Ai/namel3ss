(() => {
  const root = window.N3UIRender || {};

  function renderIngestionStatusElement(el) {
    const status = normalizeStatus(el && el.status);
    const wrapper = document.createElement("div");
    wrapper.className = `ui-element ui-ingestion-status is-${status}`;

    const header = document.createElement("div");
    header.className = "ui-ingestion-status-header";

    const badge = document.createElement("span");
    badge.className = `ui-ingestion-status-badge is-${status}`;
    badge.textContent = `Ingestion ${status}`;
    if (status === "block") {
      wrapper.classList.add("is-block");
    }
    header.appendChild(badge);

    const source = document.createElement("span");
    source.className = "ui-ingestion-status-source";
    source.textContent = typeof el.source === "string" && el.source ? el.source : "state.ingestion";
    header.appendChild(source);

    wrapper.appendChild(header);

    if (typeof el.fallback_used === "string" && el.fallback_used) {
      const fallback = document.createElement("div");
      fallback.className = "ui-ingestion-status-fallback";
      fallback.textContent = `Fallback used: ${el.fallback_used}`;
      wrapper.appendChild(fallback);
    }

    const reasons = Array.isArray(el && el.reasons) ? el.reasons.filter((entry) => typeof entry === "string" && entry) : [];
    const details = normalizeDetails(el && el.details);
    const detailsByCode = new Map(details.map((entry) => [entry.code, entry]));

    if (!reasons.length) {
      const empty = document.createElement("div");
      empty.className = "ui-ingestion-status-empty";
      empty.textContent = "No ingestion warnings.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const list = document.createElement("div");
    list.className = "ui-ingestion-status-reasons";

    reasons.forEach((code) => {
      const detail = detailsByCode.get(code);
      const item = document.createElement("div");
      item.className = "ui-ingestion-status-reason";

      const codeLabel = document.createElement("div");
      codeLabel.className = "ui-ingestion-status-code";
      codeLabel.textContent = code;
      item.appendChild(codeLabel);

      if (detail && detail.message) {
        const message = document.createElement("div");
        message.className = "ui-ingestion-status-message";
        message.textContent = detail.message;
        item.appendChild(message);
      }

      if (detail && detail.remediation) {
        const remediation = document.createElement("div");
        remediation.className = "ui-ingestion-status-remediation";
        remediation.textContent = detail.remediation;
        item.appendChild(remediation);
      }

      list.appendChild(item);
    });

    wrapper.appendChild(list);
    return wrapper;
  }

  function normalizeStatus(value) {
    if (value === "warn" || value === "block") return value;
    return "pass";
  }

  function normalizeDetails(raw) {
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((entry) => entry && typeof entry === "object")
      .map((entry) => ({
        code: typeof entry.code === "string" ? entry.code : "",
        message: typeof entry.message === "string" ? entry.message : "",
        remediation: typeof entry.remediation === "string" ? entry.remediation : "",
      }))
      .filter((entry) => entry.code);
  }

  root.renderIngestionStatusElement = renderIngestionStatusElement;
  window.N3UIRender = root;
})();
