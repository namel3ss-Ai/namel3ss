(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});
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

  traces.buildMemoryEventEntries = buildMemoryEventEntries;
  traces.buildMemoryExplanationMap = buildMemoryExplanationMap;
  traces.buildMemoryLinksMap = buildMemoryLinksMap;
  traces.buildMemoryPathMap = buildMemoryPathMap;
  traces.buildMemoryImpactMap = buildMemoryImpactMap;
  traces.buildTeamSummaryEntries = buildTeamSummaryEntries;
  traces.latestTeamSummary = latestTeamSummary;
  traces.findPhaseDiffEvent = findPhaseDiffEvent;
  traces.collectEventsForIds = collectEventsForIds;
  traces.collectImpactEventsByDepth = collectImpactEventsByDepth;
  traces.memoryIdsForEvent = memoryIdsForEvent;
})();
