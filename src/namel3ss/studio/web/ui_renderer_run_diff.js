(function () {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderRunDiffElement(el) {
    const wrapper = document.createElement("section");
    wrapper.className = "ui-element ui-run-diff";

    const heading = document.createElement("h3");
    heading.className = "ui-run-diff-heading";
    heading.textContent = "Run Comparison";
    wrapper.appendChild(heading);

    const leftRunId = textValue(el && el.left_run_id) || "none";
    const rightRunId = textValue(el && el.right_run_id) || "none";
    const changed = Boolean(el && el.changed);
    const changeCount = numericValue(el && el.change_count);

    wrapper.appendChild(metaRow("Left run", leftRunId));
    wrapper.appendChild(metaRow("Right run", rightRunId));
    wrapper.appendChild(metaRow("Changed", changed ? "yes" : "no"));
    wrapper.appendChild(metaRow("Changed fields", String(changeCount)));

    const rows = normalizeChanges(el && el.changes);
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "ui-run-diff-empty";
      empty.textContent = "No run diff available yet.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const list = document.createElement("ul");
    list.className = "ui-run-diff-list";
    rows.forEach((row) => {
      const item = document.createElement("li");
      item.className = `ui-run-diff-item ${row.changed ? "is-changed" : "is-unchanged"}`;
      const label = document.createElement("span");
      label.className = "ui-run-diff-field";
      label.textContent = row.field;
      const state = document.createElement("span");
      state.className = "ui-run-diff-state";
      state.textContent = row.changed ? "changed" : "same";
      item.appendChild(label);
      item.appendChild(state);
      list.appendChild(item);
    });
    wrapper.appendChild(list);
    return wrapper;
  }

  function normalizeChanges(value) {
    if (!Array.isArray(value)) return [];
    const rows = [];
    const seen = new Set();
    value.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const field = textValue(entry.field);
      if (!field || seen.has(field)) return;
      seen.add(field);
      rows.push({
        field: field,
        changed: Boolean(entry.changed),
      });
    });
    return rows;
  }

  function metaRow(label, value) {
    const row = document.createElement("div");
    row.className = "ui-run-diff-row";
    const left = document.createElement("span");
    left.className = "ui-run-diff-label";
    left.textContent = `${label}:`;
    const right = document.createElement("span");
    right.className = "ui-run-diff-value";
    right.textContent = value;
    row.appendChild(left);
    row.appendChild(right);
    return row;
  }

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function numericValue(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return 0;
    const whole = Math.trunc(parsed);
    return whole >= 0 ? whole : 0;
  }

  root.renderRunDiffElement = renderRunDiffElement;
  window.renderRunDiffElement = renderRunDiffElement;
})();
