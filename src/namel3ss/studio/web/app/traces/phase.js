(() => {
  const root = window.N3App || (window.N3App = {});
  const traces = root.traces || (root.traces = {});
  function currentPhaseIdForTrace(trace) {
    const events = trace.canonical_events || [];
    const recall = events.find((event) => event && event.type === "memory_recall");
    if (recall && recall.current_phase && recall.current_phase.phase_id) {
      return recall.current_phase.phase_id;
    }
    const phaseEvent = events.find((event) => event && event.type === "memory_phase_started");
    if (phaseEvent && phaseEvent.phase_id) {
      return phaseEvent.phase_id;
    }
    return null;
  }
  traces.currentPhaseIdForTrace = currentPhaseIdForTrace;
})();
