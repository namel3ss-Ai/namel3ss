(() => {
  const root = window.N3App || (window.N3App = {});
  if (root.boot) root.boot();
})();
