(() => {
  const root = window.N3App || (window.N3App = {});
  const render = root.render || (root.render = {});
  const utils = root.utils;
  const state = root.state;

  function renderState(data) {
    state.setCachedState(data || {});
    const container = document.getElementById("state");
    if (!container) return;
    container.innerHTML = "";
    const isEmpty = !data || (Object.keys(data || {}).length === 0 && data.constructor === Object);
    if (isEmpty) {
      utils.showEmpty(container, "State will appear here after you run an action.");
    } else {
      container.appendChild(utils.createCodeBlock(data));
    }
    utils.updateCopyButton("stateCopy", () => JSON.stringify(data || {}, null, 2));
  }

  render.renderState = renderState;
  window.renderState = renderState;
})();
