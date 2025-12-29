(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;
  let handlersReady = false;

  function ruleMeta(rule) {
    const parts = [];
    if (rule.scope) parts.push(`scope: ${rule.scope}`);
    if (rule.status) parts.push(`status: ${rule.status}`);
    if (rule.priority !== undefined && rule.priority !== null) parts.push(`priority: ${rule.priority}`);
    if (rule.phase_id) parts.push(`phase: ${rule.phase_id}`);
    if (rule.created_by) parts.push(`by: ${rule.created_by}`);
    return parts.join(" | ");
  }

  function renderRuleList(container, rules, emptyText, isPending) {
    if (!container) return;
    container.innerHTML = "";
    if (!rules || !rules.length) {
      utils.showEmpty(container, emptyText);
      return;
    }
    const listWrap = document.createElement("div");
    listWrap.className = "list";
    rules.forEach((rule) => {
      const item = document.createElement("div");
      item.className = "list-item rules-item";
      const title = document.createElement("div");
      title.className = "list-title";
      title.textContent = rule.text || "Rule";
      const meta = document.createElement("div");
      meta.className = "list-meta";
      meta.textContent = ruleMeta(rule);
      item.appendChild(title);
      item.appendChild(meta);
      if (isPending) {
        const actions = document.createElement("div");
        actions.className = "list-actions";
        const approveBtn = document.createElement("button");
        approveBtn.className = "btn ghost small";
        approveBtn.textContent = "Approve";
        approveBtn.onclick = () => applyRuleDecision("approve", rule.proposal_id);
        const rejectBtn = document.createElement("button");
        rejectBtn.className = "btn ghost small";
        rejectBtn.textContent = "Reject";
        rejectBtn.onclick = () => applyRuleDecision("reject", rule.proposal_id);
        actions.appendChild(approveBtn);
        actions.appendChild(rejectBtn);
        item.appendChild(actions);
      }
      listWrap.appendChild(item);
    });
    container.appendChild(listWrap);
  }

  function renderRules(data) {
    const nextValue = data || state.getCachedRules();
    state.setCachedRules(nextValue);
    const panel = document.getElementById("rulesPanel");
    if (!panel) return;
    setupRulesHandlers();
    if (!data || data.ok === false) {
      const error = (data && data.error) || "Unable to load rules";
      renderRuleList(document.getElementById("rulesActiveTeam"), [], error, false);
      renderRuleList(document.getElementById("rulesActiveSystem"), [], error, false);
      renderRuleList(document.getElementById("rulesPendingTeam"), [], error, true);
      renderRuleList(document.getElementById("rulesPendingSystem"), [], error, true);
      return;
    }
    renderRuleList(
      document.getElementById("rulesActiveTeam"),
      data.active_team || [],
      "No active team rules.",
      false
    );
    renderRuleList(
      document.getElementById("rulesActiveSystem"),
      data.active_system || [],
      "No active system rules.",
      false
    );
    renderRuleList(
      document.getElementById("rulesPendingTeam"),
      data.pending_team || [],
      "No pending team rules.",
      true
    );
    renderRuleList(
      document.getElementById("rulesPendingSystem"),
      data.pending_system || [],
      "No pending system rules.",
      true
    );
  }

  async function refreshRules() {
    const [rules, packs] = await Promise.all([
      utils.fetchJson("/api/memory/rules"),
      utils.fetchJson("/api/memory/packs"),
    ]);
    renderRules(rules);
    if (window.renderMemoryPacks) window.renderMemoryPacks(packs);
  }

  async function proposeRule() {
    const input = document.getElementById("rulesText");
    const scopeSelect = document.getElementById("rulesScope");
    const priorityInput = document.getElementById("rulesPriority");
    const text = input ? input.value.trim() : "";
    if (!text) {
      utils.showToast("Rule text is required.");
      return;
    }
    const scope = scopeSelect ? scopeSelect.value : "team";
    const priority = priorityInput ? parseInt(priorityInput.value || "0", 10) : 0;
    try {
      const resp = await fetch("/api/memory/rules/propose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, scope, priority }),
      });
      const data = await resp.json();
      if (!data.ok) {
        utils.showToast("Rule proposal failed.");
        if (data.error) utils.showToast(data.error);
        return;
      }
      if (input) input.value = "";
      if (priorityInput) priorityInput.value = "";
      if (Array.isArray(data.traces) && data.traces.length) {
        state.setCachedTraces(state.getCachedTraces().concat(data.traces));
        if (window.renderTraces) window.renderTraces(state.getCachedTraces());
      }
      renderRules(data);
    } catch (err) {
      utils.showToast("Rule proposal failed.");
    }
  }

  async function applyRuleDecision(action, proposalId) {
    if (!proposalId) {
      utils.showToast("Rule proposal id is missing.");
      return;
    }
    if (window.applyAgreementAction) {
      await window.applyAgreementAction(action, proposalId);
      refreshRules();
      return;
    }
    const res = await fetch(`/api/memory/agreements/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ proposal_id: proposalId }),
    });
    const data = await res.json();
    if (!data.ok) {
      utils.showToast("Rule approval failed.");
      if (data.error) utils.showToast(data.error);
      return;
    }
    if (Array.isArray(data.traces) && data.traces.length) {
      state.setCachedTraces(state.getCachedTraces().concat(data.traces));
      if (window.renderTraces) window.renderTraces(state.getCachedTraces());
    }
    refreshRules();
  }

  function setupRulesHandlers() {
    if (handlersReady) return;
    handlersReady = true;
    const refreshBtn = document.getElementById("rulesRefresh");
    if (refreshBtn) refreshBtn.onclick = refreshRules;
    const proposeBtn = document.getElementById("rulesPropose");
    if (proposeBtn) proposeBtn.onclick = proposeRule;
  }

  render.renderRules = renderRules;
  render.refreshRules = refreshRules;
  render.proposeRule = proposeRule;
  window.renderRules = renderRules;
  window.refreshRules = refreshRules;
})();
