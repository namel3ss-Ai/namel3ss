(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  const K_OPTIONS = [0, 1, 2, 3, 5, 8, 10, 20, 50];
  const WEIGHT_OPTIONS = [0.0, 0.25, 0.5, 0.75, 1.0];
  const CONTROL_ORDER = {
    set_semantic_k: 0,
    set_lexical_k: 1,
    set_semantic_weight: 2,
    set_final_top_k: 3,
  };
  const CONTROL_LABELS = {
    set_semantic_k: "Semantic candidates (k)",
    set_lexical_k: "Lexical candidates (k)",
    set_semantic_weight: "Semantic weight",
    set_final_top_k: "Final top-k",
  };
  const CONTROL_DEFAULTS = {
    set_semantic_k: 20,
    set_lexical_k: 20,
    set_final_top_k: 10,
    set_semantic_weight: 0.5,
  };

  function renderRetrievalExplainElement(el, handleAction) {
    const wrapper = document.createElement("section");
    wrapper.className = "ui-element ui-retrieval-explain";

    const heading = document.createElement("div");
    heading.className = "ui-retrieval-explain-heading";
    heading.textContent = "Why this answer?";
    wrapper.appendChild(heading);

    const query = typeof el.query === "string" && el.query.trim() ? el.query.trim() : "";
    if (query) {
      const queryNode = document.createElement("div");
      queryNode.className = "ui-retrieval-explain-query";
      queryNode.textContent = `Query: ${query}`;
      wrapper.appendChild(queryNode);
    }

    const controlsNode = renderRetrievalControls(el && el.retrieval_controls, handleAction);
    wrapper.appendChild(controlsNode);

    const trustNode = renderTrustSummary(el && el.trust_score_details);
    wrapper.appendChild(trustNode);

    const planNode = renderPlanSummary(el && el.retrieval_plan);
    wrapper.appendChild(planNode);

    const trace = normalizeTrace(el && el.retrieval_trace);
    if (!trace.length) {
      const empty = document.createElement("div");
      empty.className = "ui-retrieval-explain-empty";
      empty.textContent = "No retrieval evidence available.";
      wrapper.appendChild(empty);
      return wrapper;
    }

    const traceTitle = document.createElement("div");
    traceTitle.className = "ui-retrieval-explain-trace-title";
    traceTitle.textContent = "Retrieved chunks";
    wrapper.appendChild(traceTitle);

    const traceList = document.createElement("div");
    traceList.className = "ui-retrieval-explain-trace";
    trace.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "ui-retrieval-explain-row";

      const rank = document.createElement("span");
      rank.className = "ui-retrieval-explain-rank";
      rank.textContent = `#${entry.rank}`;
      row.appendChild(rank);

      const score = document.createElement("span");
      score.className = "ui-retrieval-explain-score";
      score.textContent = `score ${entry.score.toFixed(3)}`;
      row.appendChild(score);

      const reason = document.createElement("span");
      reason.className = "ui-retrieval-explain-reason";
      reason.textContent = entry.reason;
      row.appendChild(reason);

      const source = document.createElement("span");
      source.className = "ui-retrieval-explain-source";
      source.textContent = `${entry.document_id || "unknown"} · p${entry.page_number}`;
      row.appendChild(source);

      const chunk = document.createElement("span");
      chunk.className = "ui-retrieval-explain-chunk";
      chunk.textContent = entry.chunk_id;
      row.appendChild(chunk);

      traceList.appendChild(row);
    });
    wrapper.appendChild(traceList);
    return wrapper;
  }

  function renderRetrievalControls(raw, handleAction) {
    const controls = normalizeControls(raw);
    const box = document.createElement("div");
    box.className = "ui-retrieval-explain-controls";

    const title = document.createElement("div");
    title.className = "ui-retrieval-explain-controls-title";
    title.textContent = "Retrieval tuning";
    box.appendChild(title);

    if (!controls.enabled && controls.disabled_reason) {
      const disabled = document.createElement("div");
      disabled.className = "ui-retrieval-explain-controls-disabled";
      disabled.textContent = controls.disabled_reason;
      box.appendChild(disabled);
    }

    const list = document.createElement("div");
    list.className = "ui-retrieval-explain-controls-list";
    box.appendChild(list);

    controls.items.forEach((item) => {
      const field = document.createElement("div");
      field.className = "ui-retrieval-explain-control";
      if (!item.enabled) field.classList.add("is-disabled");
      if (item.disabled_reason) field.title = item.disabled_reason;

      const label = document.createElement("label");
      label.className = "ui-retrieval-explain-control-label";
      label.textContent = item.label;
      field.appendChild(label);

      if (item.flow === "set_semantic_weight") {
        field.appendChild(renderWeightControl(item, handleAction));
      } else {
        field.appendChild(renderKControl(item, handleAction));
      }
      list.appendChild(field);
    });
    return box;
  }

  function renderKControl(item, handleAction) {
    const select = document.createElement("select");
    select.className = "ui-retrieval-explain-control-input";
    const options = uniqueSortedInts(K_OPTIONS.concat([item.value]));
    options.forEach((value) => {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = String(value);
      select.appendChild(option);
    });
    select.value = String(item.value);
    const disabled = !item.enabled || typeof handleAction !== "function" || !item.action_id;
    select.disabled = disabled;
    select.addEventListener("change", async () => {
      const previous = item.value;
      const nextValue = toPositiveInt(select.value);
      item.value = nextValue;
      const ok = await executeControlAction(
        item,
        { [item.input_field]: nextValue },
        select,
        handleAction
      );
      if (!ok) {
        item.value = previous;
        select.value = String(previous);
      }
    });
    return select;
  }

  function renderWeightControl(item, handleAction) {
    const group = document.createElement("div");
    group.className = "ui-retrieval-explain-control-weight";
    const disabled = !item.enabled || typeof handleAction !== "function" || !item.action_id;
    WEIGHT_OPTIONS.forEach((value) => {
      const option = document.createElement("label");
      option.className = "ui-retrieval-explain-weight-option";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = `retrieval-weight-${item.flow}`;
      input.value = value.toFixed(2);
      input.checked = Math.abs(item.value - value) < 0.001;
      input.disabled = disabled;
      input.addEventListener("change", async () => {
        if (!input.checked) return;
        const previous = item.value;
        const nextValue = toScore(input.value);
        item.value = nextValue;
        const ok = await executeControlAction(
          item,
          { [item.input_field]: nextValue },
          input,
          handleAction
        );
        if (!ok) {
          item.value = previous;
          const fallback = group.querySelector(`input[value="${previous.toFixed(2)}"]`);
          if (fallback) fallback.checked = true;
        }
      });
      option.appendChild(input);
      const text = document.createElement("span");
      text.textContent = `${Math.round(value * 100)}%`;
      option.appendChild(text);
      group.appendChild(option);
    });
    return group;
  }

  async function executeControlAction(item, payload, source, handleAction) {
    if (typeof handleAction !== "function" || !item.action_id) return false;
    const action = {
      id: item.action_id,
      type: "call_flow",
      flow: item.flow,
      input_field: item.input_field,
    };
    try {
      const response = await handleAction(action, payload, source);
      return !(response && response.ok === false);
    } catch (_err) {
      return false;
    }
  }

  function normalizeControls(raw) {
    const value = raw && typeof raw === "object" ? raw : {};
    const items = Array.isArray(value.items) ? value.items : [];
    const normalized = items
      .filter((item) => item && typeof item === "object")
      .map((item) => normalizeControlItem(item))
      .sort((left, right) => {
        const leftOrder = CONTROL_ORDER[left.flow] ?? 999;
        const rightOrder = CONTROL_ORDER[right.flow] ?? 999;
        if (leftOrder !== rightOrder) return leftOrder - rightOrder;
        return left.flow.localeCompare(right.flow);
      });
    const enabled = normalized.some((item) => item.enabled);
    const disabled_reason =
      typeof value.disabled_reason === "string" && value.disabled_reason
        ? value.disabled_reason
        : "Retrieval tuning flows are not available.";
    return {
      enabled: enabled,
      disabled_reason: enabled ? "" : disabled_reason,
      items: normalized,
    };
  }

  function normalizeControlItem(raw) {
    const flow = typeof raw.flow === "string" ? raw.flow : "";
    const isWeight = flow === "set_semantic_weight";
    const inputField =
      typeof raw.input_field === "string" && raw.input_field ? raw.input_field : isWeight ? "weight" : "k";
    const defaultValue = CONTROL_DEFAULTS[flow] ?? (isWeight ? 0.5 : 10);
    const value = isWeight ? toScore(raw.value) : raw.value === null ? defaultValue : toPositiveInt(raw.value);
    return {
      flow: flow,
      label: CONTROL_LABELS[flow] || flow || "retrieval tuning",
      action_id: typeof raw.action_id === "string" ? raw.action_id : "",
      input_field: inputField,
      enabled: raw.enabled === true,
      disabled_reason: typeof raw.disabled_reason === "string" ? raw.disabled_reason : "",
      value: value,
    };
  }

  function renderTrustSummary(raw) {
    const details = normalizeTrustDetails(raw);
    const trust = document.createElement("div");
    trust.className = "ui-retrieval-explain-trust";

    const badge = document.createElement("span");
    badge.className = `ui-retrieval-explain-trust-badge level-${details.level}`;
    badge.textContent = `Trust ${Math.round(details.score * 100)}%`;
    trust.appendChild(badge);

    const formula = document.createElement("span");
    formula.className = "ui-retrieval-explain-trust-formula";
    formula.textContent = details.formula_version;
    trust.appendChild(formula);

    return trust;
  }

  function renderPlanSummary(raw) {
    const plan = normalizePlan(raw);
    const box = document.createElement("div");
    box.className = "ui-retrieval-explain-plan";

    const summary = document.createElement("div");
    summary.className = "ui-retrieval-explain-plan-summary";
    summary.textContent =
      `tier ${plan.tier.requested} -> ${plan.tier.selected} · ` +
      `${plan.cutoffs.selected_count}/${plan.cutoffs.candidate_count} selected`;
    box.appendChild(summary);

    const filters = Array.isArray(plan.filters) ? plan.filters : [];
    if (filters.length) {
      const filterList = document.createElement("div");
      filterList.className = "ui-retrieval-explain-filters";
      filters.forEach((entry) => {
        if (!entry || typeof entry !== "object") return;
        const item = document.createElement("div");
        item.className = "ui-retrieval-explain-filter";
        const name = typeof entry.name === "string" ? entry.name : "filter";
        item.textContent = `${name}: ${JSON.stringify(entry)}`;
        filterList.appendChild(item);
      });
      box.appendChild(filterList);
    }
    return box;
  }

  function normalizePlan(raw) {
    const value = raw && typeof raw === "object" ? raw : {};
    const tier = value.tier && typeof value.tier === "object" ? value.tier : {};
    const cutoffs = value.cutoffs && typeof value.cutoffs === "object" ? value.cutoffs : {};
    return {
      tier: {
        requested: typeof tier.requested === "string" ? tier.requested : "auto",
        selected: typeof tier.selected === "string" ? tier.selected : "none",
      },
      cutoffs: {
        selected_count: toPositiveInt(cutoffs.selected_count),
        candidate_count: toPositiveInt(cutoffs.candidate_count),
      },
      filters: Array.isArray(value.filters) ? value.filters : [],
    };
  }

  function normalizeTrustDetails(raw) {
    const value = raw && typeof raw === "object" ? raw : {};
    const score = toScore(value.score);
    const level =
      typeof value.level === "string" && value.level ? value.level : score >= 0.8 ? "high" : score >= 0.55 ? "medium" : "low";
    const formula_version =
      typeof value.formula_version === "string" && value.formula_version ? value.formula_version : "rag_trust@1";
    return { score, level, formula_version };
  }

  function normalizeTrace(raw) {
    if (!Array.isArray(raw)) return [];
    const entries = [];
    raw.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      const chunk_id = typeof entry.chunk_id === "string" ? entry.chunk_id : "";
      const reason = typeof entry.reason === "string" ? entry.reason : "";
      if (!chunk_id || !reason) return;
      entries.push({
        chunk_id: chunk_id,
        document_id: typeof entry.document_id === "string" ? entry.document_id : "",
        page_number: toPositiveInt(entry.page_number),
        score: toScore(entry.score),
        rank: toPositiveInt(entry.rank) || entries.length + 1,
        reason: reason,
      });
    });
    entries.sort((a, b) => a.rank - b.rank || a.chunk_id.localeCompare(b.chunk_id));
    return entries;
  }

  function uniqueSortedInts(values) {
    const seen = new Set();
    const out = [];
    values.forEach((value) => {
      const number = toPositiveInt(value);
      if (seen.has(number)) return;
      seen.add(number);
      out.push(number);
    });
    out.sort((a, b) => a - b);
    return out;
  }

  function toPositiveInt(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return 0;
    const whole = Math.trunc(parsed);
    if (whole <= 0) return 0;
    return whole;
  }

  function toScore(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return 0;
    if (parsed < 0) return 0;
    if (parsed > 1) return 1;
    return Math.round(parsed * 10000) / 10000;
  }

  root.renderRetrievalExplainElement = renderRetrievalExplainElement;
})();
