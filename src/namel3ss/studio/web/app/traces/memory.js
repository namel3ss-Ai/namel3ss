(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});
  const utils = root.utils;
  const state = root.state;
  const constants = root.constants;

  function buildMemoryEventEntries(trace) {
    const entries = [];
    const events = trace.canonical_events || [];
    events.forEach((event, index) => {
      if (event && constants.MEMORY_EVENT_TYPES.has(event.type)) {
        entries.push({ event, index });
      }
    });
    return entries;
  }
  function buildMemoryExplanationMap(trace) {
    const map = new Map();
    const events = trace.canonical_events || [];
    events.forEach((event) => {
      if (event && event.type === "memory_explanation") {
        const index = event.for_event_index;
        if (typeof index === "number") {
          map.set(index, event);
        }
      }
    });
    return map;
  }
  function buildMemoryLinksMap(trace) {
    const map = new Map();
    const events = trace.canonical_events || [];
    events.forEach((event) => {
      if (event && event.type === "memory_links") {
        const memoryId = event.memory_id;
        if (typeof memoryId === "string") {
          map.set(memoryId, event);
        }
      }
    });
    return map;
  }
  function buildMemoryPathMap(trace) {
    const map = new Map();
    const events = trace.canonical_events || [];
    events.forEach((event) => {
      if (event && event.type === "memory_path") {
        const memoryId = event.memory_id;
        if (typeof memoryId === "string") {
          map.set(memoryId, event);
        }
      }
    });
    return map;
  }
  function buildMemoryImpactMap(trace) {
    const map = new Map();
    const events = trace.canonical_events || [];
    events.forEach((event) => {
      if (event && event.type === "memory_impact") {
        const memoryId = event.memory_id;
        const depth = event.depth_used;
        if (typeof memoryId === "string" && typeof depth === "number") {
          const entry = map.get(memoryId) || {};
          entry[String(depth)] = event;
          map.set(memoryId, entry);
        }
      }
    });
    return map;
  }
  function buildTeamSummaryEntries(trace) {
    const events = trace.canonical_events || [];
    return events.filter((event) => event && event.type === "memory_team_summary");
  }
  function latestTeamSummary(trace) {
    const entries = buildTeamSummaryEntries(trace);
    if (!entries.length) return null;
    return entries[entries.length - 1];
  }
  function findPhaseDiffEvent(trace, summary) {
    if (!summary) return null;
    const events = trace.canonical_events || [];
    const summaryLane = summary.lane || "team";
    return events.find((event) => {
      if (!event || event.type !== "memory_phase_diff") return false;
      if (event.space !== summary.space) return false;
      if (event.from_phase_id !== summary.phase_from) return false;
      if (event.to_phase_id !== summary.phase_to) return false;
      if (event.lane && event.lane !== summaryLane) return false;
      return true;
    });
  }
  function formatTeamSummaryText(summary) {
    const lines = [];
    if (summary.title) lines.push(summary.title);
    const detail = Array.isArray(summary.lines) ? summary.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }
  function appendTeamSummaryBlock(wrapper, summary, diffEvent, renderMode) {
    const block = document.createElement("div");
    block.className = "trace-event trace-team-summary";
    const label = document.createElement("div");
    label.className = "trace-event-label";
    label.textContent = "Team summary";
    const summaryBlock = utils.createCodeBlock(formatTeamSummaryText(summary));
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
  function collectEventsForIds(map, ids) {
    const events = [];
    if (!map || !ids) return events;
    ids.forEach((memoryId) => {
      const event = map.get(memoryId);
      if (event) events.push(event);
    });
    return events;
  }
  function collectImpactEventsByDepth(map, ids) {
    const byDepth = new Map();
    if (!map || !ids) return byDepth;
    ids.forEach((memoryId) => {
      const entry = map.get(memoryId);
      if (!entry) return;
      Object.keys(entry).forEach((depth) => {
        const event = entry[depth];
        if (!event) return;
        const events = byDepth.get(depth) || [];
        events.push(event);
        byDepth.set(depth, events);
      });
    });
    return byDepth;
  }
  function memoryIdsForEvent(event) {
    if (!event || typeof event !== "object") return [];
    if (typeof event.memory_id === "string") return [event.memory_id];
    if (typeof event.to_id === "string") return [event.to_id];
    if (typeof event.winner_id === "string") return [event.winner_id];
    if (typeof event.from_id === "string") return [event.from_id];
    if (Array.isArray(event.written)) {
      return event.written.map((item) => item && item.id).filter((value) => typeof value === "string");
    }
    return [];
  }
  function formatExplanationText(explainEvent) {
    const lines = [];
    if (explainEvent.title) lines.push(explainEvent.title);
    const detail = Array.isArray(explainEvent.lines) ? explainEvent.lines : [];
    detail.forEach((line) => {
      if (line) lines.push(line);
    });
    return lines.join("\n");
  }
  function formatLinksText(linkEvents) {
    const lines = [];
    linkEvents.forEach((event) => {
      if (event.memory_id) {
        lines.push(`Memory id is ${event.memory_id}.`);
      }
      const detail = Array.isArray(event.lines) ? event.lines : [];
      detail.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    return lines.join("\n");
  }
  function formatPathText(pathEvents) {
    const lines = [];
    pathEvents.forEach((event) => {
      if (event.title) lines.push(event.title);
      if (event.memory_id) {
        lines.push(`Memory id is ${event.memory_id}.`);
      }
      const detail = Array.isArray(event.lines) ? event.lines : [];
      detail.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    return lines.join("\n");
  }
  function formatImpactText(impactEvents) {
    const lines = [];
    impactEvents.forEach((event) => {
      if (event.title) lines.push(event.title);
      if (event.memory_id) {
        lines.push(`Memory id is ${event.memory_id}.`);
      }
      const detail = Array.isArray(event.lines) ? event.lines : [];
      detail.forEach((line) => {
        if (line) lines.push(line);
      });
      const pathDetail = Array.isArray(event.path_lines) ? event.path_lines : [];
      pathDetail.forEach((line) => {
        if (line) lines.push(line);
      });
    });
    return lines.join("\n");
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
      impactBlock.textContent = formatImpactText(events);
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
  function appendMemoryEventsSection(details, trace, phaseId, renderMode = "json") {
    const laneMode = state.getTraceLaneMode();
    const phaseMode = state.getTracePhaseMode();
    const events = buildMemoryEventEntries(trace);
    if (!events.length) return;
    const explainMap = buildMemoryExplanationMap(trace);
    const linksMap = buildMemoryLinksMap(trace);
    const pathMap = buildMemoryPathMap(trace);
    const impactMap = buildMemoryImpactMap(trace);
    const wrapper = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "inline-label";
    heading.textContent = "Memory events";
    wrapper.appendChild(heading);
    const teamSummary = laneMode === "team" ? latestTeamSummary(trace) : null;
    if (teamSummary) {
      const diffEvent = findPhaseDiffEvent(trace, teamSummary);
      appendTeamSummaryBlock(wrapper, teamSummary, diffEvent, renderMode);
    }
    events.forEach((entry) => {
      const filtered = filterMemoryEventForPhase(entry.event, phaseId, phaseMode);
      if (!filtered) return;
      const laneFiltered = filterMemoryEventForLane(filtered, laneMode);
      if (!laneFiltered) return;
      if (teamSummary && laneFiltered.type === "memory_team_summary") return;
      const block = document.createElement("div");
      block.className = "trace-event";
      const label = document.createElement("div");
      label.className = "trace-event-label";
      label.textContent = laneFiltered.type || "memory_event";
      const memoryIds = memoryIdsForEvent(laneFiltered);
      const linkEvents = collectEventsForIds(linksMap, memoryIds);
      const pathEvents = collectEventsForIds(pathMap, memoryIds);
      const impactEventsByDepth = collectImpactEventsByDepth(impactMap, memoryIds);
      const isLinkEvent = laneFiltered.type === "memory_links" || laneFiltered.type === "memory_path";
      const isImpactEvent = laneFiltered.type === "memory_impact" || laneFiltered.type === "memory_change_preview";
      const explain = explainMap.get(entry.index);
      const contentBlock = utils.createCodeBlock(renderMode === "plain" ? traces.renderPlainTraceValue(laneFiltered) : laneFiltered);
      if (explain) {
        const explainBtn = document.createElement("button");
        explainBtn.className = "btn ghost small";
        explainBtn.textContent = "Explain";
        label.appendChild(explainBtn);
        const explainText = formatExplanationText(explain);
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
          const linksText = formatLinksText(linkEvents);
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
          const pathText = formatPathText(pathEvents);
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
        const linksText = formatLinksText(linkEvents);
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
        const pathText = formatPathText(pathEvents);
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

  traces.appendMemoryEventsSection = appendMemoryEventsSection;
  traces.buildMemoryEventEntries = buildMemoryEventEntries;
  traces.buildMemoryExplanationMap = buildMemoryExplanationMap;
  traces.buildMemoryLinksMap = buildMemoryLinksMap;
  traces.buildMemoryPathMap = buildMemoryPathMap;
  traces.buildMemoryImpactMap = buildMemoryImpactMap;
  traces.memoryIdsForEvent = memoryIdsForEvent;
  traces.filterMemoryEventForPhase = filterMemoryEventForPhase;
  traces.filterMemoryEventForLane = filterMemoryEventForLane;
  traces.collectEventsForIds = collectEventsForIds;
  traces.collectImpactEventsByDepth = collectImpactEventsByDepth;
  traces.appendImpactControls = appendImpactControls;
  traces.defaultImpactDepth = defaultImpactDepth;
  traces.formatExplanationText = formatExplanationText;
  traces.formatLinksText = formatLinksText;
  traces.formatPathText = formatPathText;
  traces.formatImpactText = formatImpactText;
  traces.latestTeamSummary = latestTeamSummary;
  traces.findPhaseDiffEvent = findPhaseDiffEvent;
  traces.formatTeamSummaryText = formatTeamSummaryText;
  traces.appendTeamSummaryBlock = appendTeamSummaryBlock;
})();
