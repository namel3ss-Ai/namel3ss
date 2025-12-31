(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const menu = root.menu || (root.menu = {});

  function setMenuOpen(menuEl, toggle, open) {
    if (!menuEl || !toggle) return;
    menuEl.classList.toggle("hidden", !open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function updateMenuState() {
    const menuEl = document.getElementById("studioMenu");
    if (!menuEl || !state) return;
    const seed = menuEl.querySelector('[data-action="seed"]');
    const reset = menuEl.querySelector('[data-action="reset"]');
    const replay = menuEl.querySelector('[data-action="replay"]');
    const exportBtn = menuEl.querySelector('[data-action="export"]');
    if (seed) seed.disabled = !state.getSeedActionId();
    if (reset) reset.disabled = !state.getResetActionId();
    if (replay) replay.disabled = !state.getLastAction();
    if (exportBtn) exportBtn.disabled = !(state.getCachedTraces() || []).length;
  }

  function runMenuAction(action) {
    if (!root.run) return;
    if (action === "seed" && root.run.runSeedAction) root.run.runSeedAction();
    if (action === "reset" && root.run.runResetAction) root.run.runResetAction();
    if (action === "replay" && root.run.replayLastAction) root.run.replayLastAction();
    if (action === "export" && root.run.exportTraces) root.run.exportTraces();
  }

  function setupMenu() {
    const toggle = document.getElementById("studioMenuToggle");
    const menuEl = document.getElementById("studioMenu");
    if (!toggle || !menuEl) return;

    const close = () => setMenuOpen(menuEl, toggle, false);
    const open = () => setMenuOpen(menuEl, toggle, true);

    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = !menuEl.classList.contains("hidden");
      if (isOpen) {
        close();
      } else {
        open();
      }
    });

    Array.from(menuEl.querySelectorAll(".menu-item")).forEach((item) => {
      item.addEventListener("click", () => {
        runMenuAction(item.dataset.action);
        close();
      });
    });

    document.addEventListener("click", (event) => {
      if (!menuEl.contains(event.target) && event.target !== toggle) {
        close();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });

    updateMenuState();
  }

  menu.setupMenu = setupMenu;
  menu.updateMenuState = updateMenuState;
})();
