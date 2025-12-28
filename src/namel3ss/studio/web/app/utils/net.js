(() => {
  const root = window.N3App || (window.N3App = {});
  const utils = root.utils || (root.utils = {});
  function fetchJson(path, options) {
    return fetch(path, options).then((res) => res.json());
  }
  utils.fetchJson = fetchJson;
})();
