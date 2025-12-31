(() => {
  const base = "/app/";
  const files = [
    "state.js",
    "constants.js",
    "utils/clipboard.js",
    "utils/net.js",
    "utils/dom.js",
    "utils/toast.js",
    "traces/phase.js",
    "traces/sections.js",
    "traces/memory_maps.js",
    "traces/memory_format.js",
    "traces/memory.js",
    "traces/render.js",
    "render/memory.js",
    "render/why.js",
    "api/actions.js",
    "api/refresh.js",
    "setup/tabs.js",
    "setup/filters.js",
    "setup/buttons.js",
    "boot.js",
    "index.js",
  ];
  files.forEach((file) => {
    document.write(`<script src=\"${base}${file}\"><\\/script>`);
  });
})();
