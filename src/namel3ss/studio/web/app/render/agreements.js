(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function latestAgreementSummary(traces) {
    const events = [];
    (traces || []).forEach((trace) => {
      const entries = trace && trace.canonical_events ? trace.canonical_events : [];
      entries.forEach((event) => {
        if (event && event.type === "memory_agreement_summary") {
          events.push(event);
        }
      });
    });
    if (!events.length) return null;
    return events[events.length - 1];
  }

  function formatAgreementSummaryText(summary) {
    const lines = [];
    if (summary.title) lines.push(summary.title);
    const detail = Array.isArray(summary.lines) ? summary.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }

  function latestTrustCheck(traces) {
    const events = [];
    (traces || []).forEach((trace) => {
      const entries = trace && trace.canonical_events ? trace.canonical_events : [];
      entries.forEach((event) => {
        if (event && event.type === "memory_trust_check" && event.allowed === false) {
          events.push(event);
        }
      });
    });
    if (!events.length) return null;
    return events[events.length - 1];
  }

  function formatTrustLines(trust) {
    const lines = [];
    if (!trust) return "";
    const detail = Array.isArray(trust.lines) ? trust.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }

  function formatTrustNotice(traces) {
    const event = latestTrustCheck(traces);
    if (!event) return "";
    const lines = [];
    if (event.title) lines.push(event.title);
    const detail = Array.isArray(event.lines) ? event.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }

  function renderAgreements(data) {
    const nextValue = data || state.getCachedAgreements();
    state.setCachedAgreements(nextValue);
    const panel = document.getElementById("teamAgreements");
    const list = document.getElementById("teamAgreementsList");
    const summaryBlock = document.getElementById("teamAgreementSummary");
    const trustLines = document.getElementById("teamTrustLines");
    const trustNotice = document.getElementById("teamTrustNotice");
    if (!panel || !list) return;
    if (state.getTraceLaneMode() !== "team") {
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    list.innerHTML = "";
    if (summaryBlock) {
      const summary = latestAgreementSummary(state.getCachedTraces());
      summaryBlock.textContent = summary ? formatAgreementSummaryText(summary) : "No agreement summary yet.";
    }
    if (trustLines) {
      trustLines.textContent = formatTrustLines((data && data.trust) || state.getCachedAgreements().trust);
    }
    if (trustNotice) {
      trustNotice.textContent = formatTrustNotice(state.getCachedTraces());
    }
    if (!data || data.ok === false) {
      utils.showEmpty(list, data && data.error ? data.error : "Unable to load agreements");
      return;
    }
    const proposals = data.proposals || [];
    if (!proposals.length) {
      utils.showEmpty(list, "No pending proposals.");
      return;
    }
    const listWrap = document.createElement("div");
    listWrap.className = "list";
    proposals.forEach((proposal) => {
      const item = document.createElement("div");
      item.className = "list-item agreement-item";
      const title = document.createElement("div");
      title.className = "list-title";
      title.textContent = proposal.title || "Team memory proposal";
      const meta = document.createElement("div");
      meta.className = "list-meta";
      const parts = [];
      if (proposal.status) parts.push(`status: ${proposal.status}`);
      if (proposal.status_line) parts.push(proposal.status_line);
      if (proposal.approval_required !== undefined && proposal.approval_count !== undefined) {
        parts.push(`approvals: ${proposal.approval_count} of ${proposal.approval_required}`);
      }
      if (proposal.proposed_by) parts.push(`by: ${proposal.proposed_by}`);
      if (proposal.phase_id) parts.push(`phase: ${proposal.phase_id}`);
      if (proposal.preview) parts.push(`preview: ${proposal.preview}`);
    meta.textContent = parts.join(" \u00b7 ");
      const actions = document.createElement("div");
      actions.className = "list-actions";
      const approveBtn = document.createElement("button");
      approveBtn.className = "btn ghost small";
      approveBtn.textContent = "Approve";
      approveBtn.onclick = () => applyAgreementAction("approve", proposal.proposal_id);
      const rejectBtn = document.createElement("button");
      rejectBtn.className = "btn ghost small";
      rejectBtn.textContent = "Reject";
      rejectBtn.onclick = () => applyAgreementAction("reject", proposal.proposal_id);
      actions.appendChild(approveBtn);
      actions.appendChild(rejectBtn);
      item.appendChild(title);
      item.appendChild(meta);
      item.appendChild(actions);
      listWrap.appendChild(item);
    });
    list.appendChild(listWrap);
  }

  async function refreshAgreements() {
    if (state.getTraceLaneMode() !== "team") {
      renderAgreements(state.getCachedAgreements());
      return;
    }
    const data = await utils.fetchJson("/api/memory/agreements");
    renderAgreements(data);
  }

  async function applyAgreementAction(action, proposalId) {
    const res = await fetch(`/api/memory/agreements/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proposal_id: proposalId }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast("Agreement action failed.");
      if (data.error) utils.showToast(data.error);
      return;
    }
    if (Array.isArray(data.traces) && data.traces.length) {
      state.setCachedTraces(state.getCachedTraces().concat(data.traces));
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    }
    renderAgreements(data);
  }

  render.renderAgreements = renderAgreements;
  render.refreshAgreements = refreshAgreements;
  render.applyAgreementAction = applyAgreementAction;
  render.latestAgreementSummary = latestAgreementSummary;
  render.formatAgreementSummaryText = formatAgreementSummaryText;
  render.latestTrustCheck = latestTrustCheck;
  render.formatTrustLines = formatTrustLines;
  render.formatTrustNotice = formatTrustNotice;
  window.renderAgreements = renderAgreements;
  window.refreshAgreements = refreshAgreements;
  window.applyAgreementAction = applyAgreementAction;

  if (root.traces && root.traces.setAgreementsRenderer) {
    root.traces.setAgreementsRenderer(renderAgreements);
  }
})();
