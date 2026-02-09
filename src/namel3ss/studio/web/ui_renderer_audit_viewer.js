(function () {
  function renderAuditViewerElement(el) {
    const wrapper = document.createElement("section");
    wrapper.className = "ui-element ui-audit-viewer";

    const heading = document.createElement("h3");
    heading.className = "ui-audit-viewer-heading";
    heading.textContent = "Run History / Audit Viewer";
    wrapper.appendChild(heading);

    const runId = textValue(el && el.run_id);
    const schemaVersion = textValue(el && el.schema_version);
    const policy = toObject(el && el.audit_policy_status);
    const bundle = toObject(el && el.audit_bundle);
    const checksums = toObject(el && el.checksums);
    const retrievalCount = numericValue(el && el.retrieval_count);
    const runtimeErrorCount = numericValue(el && el.runtime_error_count);

    wrapper.appendChild(metaRow("Run id", runId || "none"));
    wrapper.appendChild(metaRow("Schema", schemaVersion || "unknown"));
    wrapper.appendChild(metaRow("Policy mode", textValue(policy.mode) || "optional"));
    wrapper.appendChild(metaRow("Bundle hash", textValue(bundle.integrity_hash) || "none"));
    wrapper.appendChild(metaRow("Retrieval rows", String(retrievalCount)));
    wrapper.appendChild(metaRow("Runtime errors", String(runtimeErrorCount)));

    const replayHint = document.createElement("div");
    replayHint.className = "ui-audit-viewer-replay";
    const runPath = textValue(bundle.run_artifact_path);
    if (runPath) {
      replayHint.textContent = `Replay this run: n3 replay --artifact .namel3ss/${runPath}`;
    } else if (runId) {
      replayHint.textContent = `Replay this run: n3 replay --artifact .namel3ss/audit/${runId}/run_artifact.json`;
    } else {
      replayHint.textContent = "Replay this run: n3 replay --artifact .namel3ss/audit/last/run_artifact.json";
    }
    wrapper.appendChild(replayHint);

    const checksumTitle = document.createElement("div");
    checksumTitle.className = "ui-audit-viewer-checksum-title";
    checksumTitle.textContent = "Deterministic checksums";
    wrapper.appendChild(checksumTitle);

    const checksumList = document.createElement("ul");
    checksumList.className = "ui-audit-viewer-checksum-list";
    for (const key of ["inputs_hash", "retrieval_trace_hash", "prompt_hash", "capability_usage_hash", "output_hash"]) {
      const value = textValue(checksums[key]) || "none";
      const item = document.createElement("li");
      item.className = "ui-audit-viewer-checksum-item";
      item.textContent = `${key}: ${value}`;
      checksumList.appendChild(item);
    }
    wrapper.appendChild(checksumList);

    const details = document.createElement("details");
    details.className = "ui-audit-viewer-details";
    const summary = document.createElement("summary");
    summary.textContent = "Inspect run artifact";
    details.appendChild(summary);
    const pre = document.createElement("pre");
    pre.className = "ui-audit-viewer-json";
    pre.textContent = stringifySafe(toObject(el && el.run_artifact));
    details.appendChild(pre);
    wrapper.appendChild(details);

    return wrapper;
  }

  function metaRow(label, value) {
    const row = document.createElement("div");
    row.className = "ui-audit-viewer-row";
    const left = document.createElement("span");
    left.className = "ui-audit-viewer-label";
    left.textContent = `${label}:`;
    const right = document.createElement("span");
    right.className = "ui-audit-viewer-value";
    right.textContent = value;
    row.appendChild(left);
    row.appendChild(right);
    return row;
  }

  function toObject(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function textValue(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function numericValue(value) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
  }

  function stringifySafe(value) {
    try {
      return JSON.stringify(value || {}, null, 2);
    } catch (_err) {
      return "{}";
    }
  }

  window.renderAuditViewerElement = renderAuditViewerElement;
})();
