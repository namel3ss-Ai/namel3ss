(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});
  const utils = root.utils;
  const state = root.state;
  const budgetEventTypes = new Set([
    "memory_budget",
    "memory_compaction",
    "memory_cache_hit",
    "memory_cache_miss",
  ]);

  function buildBudgetEventEntries(trace) {
    const entries = [];
    const events = trace.canonical_events || [];
    events.forEach((event, index) => {
      if (event && budgetEventTypes.has(event.type)) {
        entries.push({ event, index });
      }
    });
    return entries;
  }
  function compactionSummaryLine(event) {
    const reason = event.reason || "";
    if (reason === "short_term_limit") return "Short term memory was compacted.";
    if (reason === "semantic_limit") return "Semantic memory was compacted.";
    if (reason === "profile_limit") return "Profile memory was compacted.";
    if (reason === "team_limit") return "Team memory was compacted.";
    if (reason === "agent_limit") return "Agent memory was compacted.";
    if (reason === "phase_limit") return "Phase memory was compacted.";
    if (event.action === "delete_low_value") return "Low value memory was removed.";
    if (event.action === "deny_write") return "Memory write was denied.";
    return "Memory was compacted.";
  }
  function budgetLinesForEvent(event) {
    if (!event || typeof event !== "object") return [];
    if (event.type === "memory_budget") {
      return Array.isArray(event.lines) ? event.lines : [];
    }
    if (event.type === "memory_cache_hit" || event.type === "memory_cache_miss") {
      return Array.isArray(event.lines) ? event.lines : [];
    }
    if (event.type === "memory_compaction") {
      const lines = [];
      const summary = compactionSummaryLine(event);
      if (summary) lines.push(summary);
      if (typeof event.items_removed_count === "number") {
        lines.push(`Items removed are ${event.items_removed_count}.`);
      }
      if (event.summary_written === true) {
        lines.push("Summary was written.");
      }
      if (event.summary_written === false) {
        lines.push("Summary was not written.");
      }
      return lines;
    }
    return [];
  }
  function appendTeamSummaryBlock(wrapper, summary, diffEvent, renderMode) {
    const block = document.createElement("div");
    block.className = "trace-event trace-team-summary";
    const label = document.createElement("div");
    label.className = "trace-event-label";
    label.textContent = "Team summary";
    const summaryBlock = utils.createCodeBlock(traces.formatTeamSummaryText(summary));
    block.appendChild(label);
    block.appendChild(summaryBlock);
    if (diffEvent) {
      const diffBtn = document.createElement("button");
      diffBtn.className = "btn ghost small";
      diffBtn.textContent = "Show diff";
      label.appendChild(diffBtn);
      const diffBlock = utils.createCodeBlock(renderMode === "plain" ? traces.renderPlainTraceValue(diffEvent) : diffEvent);
      diffBlock.classList.add("trace-links");
      diffBlock.style.display = "none";
      diffBtn.onclick = () => {
        const nextState = diffBlock.style.display === "none" ? "block" : "none";
        diffBlock.style.display = nextState;
      };
      block.appendChild(diffBlock);
    }
    wrapper.appendChild(block);
  }
  function defaultImpactDepth(impactByDepth) {
    if (!impactByDepth || impactByDepth.size === 0) return null;
    if (impactByDepth.has("1")) return "1";
    if (impactByDepth.has("2")) return "2";
    const keys = Array.from(impactByDepth.keys()).sort();
    return keys[0] || null;
  }
  function appendImpactControls(block, label, impactByDepth) {
    if (!impactByDepth || impactByDepth.size === 0) return;
    const impactBtn = document.createElement("button");
    impactBtn.className = "btn ghost small";
    impactBtn.textContent = "Impact";
    label.appendChild(impactBtn);

    const impactWrapper = document.createElement("div");
    impactWrapper.className = "trace-impact";
    impactWrapper.style.display = "none";

    const depthRow = document.createElement("div");
    depthRow.className = "trace-impact-depth";
    const depth1Btn = document.createElement("button");
    depth1Btn.className = "btn ghost small";
    depth1Btn.textContent = "Depth 1";
    const depth2Btn = document.createElement("button");
    depth2Btn.className = "btn ghost small";
    depth2Btn.textContent = "Depth 2";
    depthRow.appendChild(depth1Btn);
    depthRow.appendChild(depth2Btn);

    const impactBlock = utils.createCodeBlock("");
    impactBlock.classList.add("trace-links");

    const updateDepth = (depthKey) => {
      const events = impactByDepth.get(depthKey) || [];
      impactBlock.textContent = traces.formatImpactText(events);
      depth1Btn.classList.toggle("toggle-active", depthKey === "1");
      depth2Btn.classList.toggle("toggle-active", depthKey === "2");
    };

    const initialDepth = defaultImpactDepth(impactByDepth);
    if (initialDepth) {
      updateDepth(initialDepth);
    }

    depth1Btn.disabled = !impactByDepth.has("1");
    depth2Btn.disabled = !impactByDepth.has("2");

    depth1Btn.onclick = () => updateDepth("1");
    depth2Btn.onclick = () => updateDepth("2");
    impactBtn.onclick = () => {
      const nextState = impactWrapper.style.display === "none" ? "block" : "none";
      impactWrapper.style.display = nextState;
    };

    impactWrapper.appendChild(depthRow);
    impactWrapper.appendChild(impactBlock);
    block.appendChild(impactWrapper);
  }
  function filterMemoryEventForPhase(event, phaseId, mode) {
    if (!event || mode !== "current" || !phaseId) return event;
    if (event.type === "memory_recall" && Array.isArray(event.recalled)) {
      const filtered = event.recalled.filter((item) => item && item.meta && item.meta.phase_id === phaseId);
      if (filtered.length === event.recalled.length) return event;
      const next = { ...event, recalled: filtered };
      return next;
    }
    if (event.phase_id && event.phase_id !== phaseId) return null;
    return event;
  }
  function filterMemoryEventForLane(event, laneMode) {
    if (!event || !laneMode) return event;
    if (event.type === "memory_recall" && Array.isArray(event.recalled)) {
      const filtered = event.recalled.filter((item) => item && item.meta && item.meta.lane === laneMode);
      if (!filtered.length) return null;
      const next = { ...event, recalled: filtered };
      return next;
    }
    if (event.type === "memory_write" && Array.isArray(event.written)) {
      const filtered = event.written.filter((item) => item && item.meta && item.meta.lane === laneMode);
      if (!filtered.length) return null;
      const next = { ...event, written: filtered };
      return next;
    }
    if (event.type === "memory_denied" && event.attempted && event.attempted.meta) {
      if (event.attempted.meta.lane !== laneMode) return null;
      return event;
    }
    if (event.type === "memory_team_summary") {
      return laneMode === "team" ? event : null;
    }
    if (event.lane) {
      return event.lane === laneMode ? event : null;
    }
    if (event.from_lane || event.to_lane) {
      if (event.from_lane === laneMode || event.to_lane === laneMode) return event;
      return null;
    }
    return event;
  }
  function appendMemoryBudgetSection(details, trace, phaseId) {
    const laneMode = state.getTraceLaneMode();
    const phaseMode = state.getTracePhaseMode();
    const filters = state.getMemoryBudgetFilters ? state.getMemoryBudgetFilters() : {};
    const entries = buildBudgetEventEntries(trace);
    if (!entries.length) return;
    const lines = [];
    entries.forEach((entry) => {
      const filtered = filterMemoryEventForPhase(entry.event, phaseId, phaseMode);
      if (!filtered) return;
      const laneFiltered = filterMemoryEventForLane(filtered, laneMode);
      if (!laneFiltered) return;
      if (filters[laneFiltered.type] === false) return;
      const eventLines = budgetLinesForEvent(laneFiltered);
      eventLines.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    if (!lines.length) return;
    const wrapper = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = "Memory budget";
    wrapper.appendChild(heading);
    wrapper.appendChild(utils.createCodeBlock(lines.join("\n")));
    details.appendChild(wrapper);
  }
  function appendMemoryEventsSection(details, trace, phaseId, renderMode = "json") {
    const laneMode = state.getTraceLaneMode();
    const phaseMode = state.getTracePhaseMode();
    const events = traces.buildMemoryEventEntries(trace);
    if (!events.length) return;
    const explainMap = traces.buildMemoryExplanationMap(trace);
    const linksMap = traces.buildMemoryLinksMap(trace);
    const pathMap = traces.buildMemoryPathMap(trace);
    const impactMap = traces.buildMemoryImpactMap(trace);
    const wrapper = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = "Memory events";
    wrapper.appendChild(heading);
    const teamSummary = laneMode === "team" ? traces.latestTeamSummary(trace) : null;
    if (teamSummary) {
      const diffEvent = traces.findPhaseDiffEvent(trace, teamSummary);
      appendTeamSummaryBlock(wrapper, teamSummary, diffEvent, renderMode);
    }
    events.forEach((entry) => {
      const filtered = filterMemoryEventForPhase(entry.event, phaseId, phaseMode);
      if (!filtered) return;
      const laneFiltered = filterMemoryEventForLane(filtered, laneMode);
      if (!laneFiltered) return;
      if (budgetEventTypes.has(laneFiltered.type)) {
        const filters = state.getMemoryBudgetFilters ? state.getMemoryBudgetFilters() : {};
        if (filters[laneFiltered.type] === false) return;
      }
      if (teamSummary && laneFiltered.type === "memory_team_summary") return;
      const block = document.createElement("div");
      block.className = "trace-event";
      const label = document.createElement("div");
      label.className = "trace-event-label";
      label.textContent = laneFiltered.type || "memory_event";
      const memoryIds = traces.memoryIdsForEvent(laneFiltered);
      const linkEvents = traces.collectEventsForIds(linksMap, memoryIds);
      const pathEvents = traces.collectEventsForIds(pathMap, memoryIds);
      const impactEventsByDepth = traces.collectImpactEventsByDepth(impactMap, memoryIds);
      const isLinkEvent = laneFiltered.type === "memory_links" || laneFiltered.type === "memory_path";
      const isImpactEvent = laneFiltered.type === "memory_impact" || laneFiltered.type === "memory_change_preview";
      const explain = explainMap.get(entry.index);
      const contentBlock = utils.createCodeBlock(renderMode === "plain" ? traces.renderPlainTraceValue(laneFiltered) : laneFiltered);
      if (explain) {
        const explainBtn = document.createElement("button");
        explainBtn.className = "btn ghost small";
        explainBtn.textContent = "Explain";
        label.appendChild(explainBtn);
        const explainText = traces.formatExplanationText(explain);
        const explainBlock = utils.createCodeBlock(explainText);
        explainBlock.classList.add("trace-explain");
        explainBlock.style.display = "none";
        explainBtn.onclick = () => {
          const nextState = explainBlock.style.display === "none" ? "block" : "none";
          explainBlock.style.display = nextState;
        };
        block.appendChild(label);
        block.appendChild(contentBlock);
        block.appendChild(explainBlock);
        if (!isLinkEvent && linkEvents.length) {
          const linksBtn = document.createElement("button");
          linksBtn.className = "btn ghost small";
          linksBtn.textContent = "Links";
          label.appendChild(linksBtn);
          const linksText = traces.formatLinksText(linkEvents);
          const linksBlock = utils.createCodeBlock(linksText);
          linksBlock.classList.add("trace-links");
          linksBlock.style.display = "none";
          linksBtn.onclick = () => {
            const nextState = linksBlock.style.display === "none" ? "block" : "none";
            linksBlock.style.display = nextState;
          };
          block.appendChild(linksBlock);
        }
        if (!isLinkEvent && pathEvents.length) {
          const pathBtn = document.createElement("button");
          pathBtn.className = "btn ghost small";
          pathBtn.textContent = "Path";
          label.appendChild(pathBtn);
          const pathText = traces.formatPathText(pathEvents);
          const pathBlock = utils.createCodeBlock(pathText);
          pathBlock.classList.add("trace-links");
          pathBlock.style.display = "none";
          pathBtn.onclick = () => {
            const nextState = pathBlock.style.display === "none" ? "block" : "none";
            pathBlock.style.display = nextState;
          };
          block.appendChild(pathBlock);
        }
        if (!isLinkEvent && !isImpactEvent) {
          appendImpactControls(block, label, impactEventsByDepth);
        }
        wrapper.appendChild(block);
        return;
      }
      block.appendChild(label);
      block.appendChild(contentBlock);
      if (!isLinkEvent && linkEvents.length) {
        const linksBtn = document.createElement("button");
        linksBtn.className = "btn ghost small";
        linksBtn.textContent = "Links";
        label.appendChild(linksBtn);
        const linksText = traces.formatLinksText(linkEvents);
        const linksBlock = utils.createCodeBlock(linksText);
        linksBlock.classList.add("trace-links");
        linksBlock.style.display = "none";
        linksBtn.onclick = () => {
          const nextState = linksBlock.style.display === "none" ? "block" : "none";
          linksBlock.style.display = nextState;
        };
        block.appendChild(linksBlock);
      }
      if (!isLinkEvent && pathEvents.length) {
        const pathBtn = document.createElement("button");
        pathBtn.className = "btn ghost small";
        pathBtn.textContent = "Path";
        label.appendChild(pathBtn);
        const pathText = traces.formatPathText(pathEvents);
        const pathBlock = utils.createCodeBlock(pathText);
        pathBlock.classList.add("trace-links");
        pathBlock.style.display = "none";
        pathBtn.onclick = () => {
          const nextState = pathBlock.style.display === "none" ? "block" : "none";
          pathBlock.style.display = nextState;
        };
        block.appendChild(pathBlock);
      }
      if (!isLinkEvent && !isImpactEvent) {
        appendImpactControls(block, label, impactEventsByDepth);
      }
      wrapper.appendChild(block);
    });
    details.appendChild(wrapper);
  }

  traces.appendMemoryBudgetSection = appendMemoryBudgetSection;
  traces.appendMemoryEventsSection = appendMemoryEventsSection;
  traces.filterMemoryEventForPhase = filterMemoryEventForPhase;
  traces.filterMemoryEventForLane = filterMemoryEventForLane;
  traces.appendImpactControls = appendImpactControls;
  traces.defaultImpactDepth = defaultImpactDepth;
  traces.appendTeamSummaryBlock = appendTeamSummaryBlock;
})();
