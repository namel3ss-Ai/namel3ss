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
    "render/summary.js",
    "render/actions.js",
    "render/lint.js",
    "render/tools.js",
    "render/packs.js",
    "render/security.js",
    "render/state.js",
    "render/agreements.js",
    "render/rules.js",
    "render/handoff.js",
    "api/actions.js",
    "api/edit.js",
    "api/refresh.js",
    "setup/tabs.js",
    "setup/filters.js",
    "setup/toggles.js",
    "setup/buttons.js",
    "boot.js",
    "index.js",
  ];
  files.forEach((file) => {
    document.write(`<script src=\"${base}${file}\"><\\/script>`);
  });
})();
