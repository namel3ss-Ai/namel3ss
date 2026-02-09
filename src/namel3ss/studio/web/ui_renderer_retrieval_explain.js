(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});

  function renderRetrievalExplainElement(el) {
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
    const level = typeof value.level === "string" && value.level ? value.level : score >= 0.8 ? "high" : score >= 0.55 ? "medium" : "low";
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
    return parsed;
  }

  root.renderRetrievalExplainElement = renderRetrievalExplainElement;
})();
