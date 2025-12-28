(() => {
  const root = window.N3App || (window.N3App = {});
  const setup = root.setup || (root.setup = {});

  function setupTabs() {
    const tabs = Array.from(document.querySelectorAll(".tab"));
    const panels = Array.from(document.querySelectorAll(".panel[data-tab]"));
    const setActive = (name) => {
      tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
      panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.tab === name));
    };
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => setActive(tab.dataset.tab));
    });
    setActive("summary");
  }

  setup.setupTabs = setupTabs;
})();
