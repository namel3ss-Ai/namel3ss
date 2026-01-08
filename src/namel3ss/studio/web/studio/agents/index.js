(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const dom = root.dom;
  const net = root.net;
  const agents = root.agents || (root.agents = {});

  let cachedPayload = null;

  function getContainer() {
    return document.getElementById("agents");
  }

  async function refreshAgents() {
    const container = getContainer();
    if (!container) return;
    try {
      const payload = await net.fetchJson("/api/agents");
      if (payload && payload.ok === false) {
        dom.showError(container, payload.error || "Unable to load agents.");
        return;
      }
      cachedPayload = payload;
      if (state && typeof state.setCachedAgents === "function") {
        state.setCachedAgents(payload);
      }
      renderAgents(payload);
    } catch (err) {
      dom.showError(container, err && err.message ? err.message : "Unable to load agents.");
    }
  }

  function renderAgents(payload) {
    const container = getContainer();
    if (!container) return;
    container.innerHTML = "";
    const data = payload || cachedPayload || (state && state.getCachedAgents && state.getCachedAgents());
    if (!data) {
      dom.showEmpty(container, "No agent data yet.");
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "agent-panel";

    const wizard = agents.wizard;
    const memoryPacks = agents.memoryPacks;
    const runner = agents.run;
    const handoff = agents.handoff;

    if (wizard && wizard.buildWizardSection) {
      wrapper.appendChild(
        wizard.buildWizardSection(data, {
          onUpdate: () => renderAgents(data),
          onRefresh: refreshAgents,
        })
      );
    }
    if (memoryPacks && memoryPacks.buildMemoryPacksSection) {
      wrapper.appendChild(memoryPacks.buildMemoryPacksSection(data, refreshAgents));
    }
    if (runner && runner.buildRunSection) {
      wrapper.appendChild(runner.buildRunSection(data));
    }
    if (handoff && handoff.buildHandoffSection) {
      wrapper.appendChild(handoff.buildHandoffSection(data, refreshAgents));
    }

    container.appendChild(wrapper);
  }

  function setupAgents() {
    const container = getContainer();
    if (!container) return;
  }

  agents.refreshAgents = refreshAgents;
  agents.renderAgents = renderAgents;
  agents.setupAgents = setupAgents;
})();
