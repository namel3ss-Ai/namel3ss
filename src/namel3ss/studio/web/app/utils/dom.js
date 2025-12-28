(() => {
  const root = window.N3App || (window.N3App = {});
  const utils = root.utils || (root.utils = {});
  const state = root.state;
  function updateCopyButton(id, getter) {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.onclick = () => window.copyText(getter());
  }
  function showEmpty(container, message) {
    container.innerHTML = "";
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = message;
    container.appendChild(empty);
  }
  function createCodeBlock(content) {
    const pre = document.createElement("pre");
    pre.className = "code-block";
    pre.textContent = typeof content === "string" ? content : JSON.stringify(content, null, 2);
    return pre;
  }
  function setFileName(path) {
    const label = document.getElementById("fileName");
    if (!label) return;
    if (!path) {
      label.textContent = "";
      return;
    }
    const parts = path.split(/[\\/]/);
    label.textContent = parts[parts.length - 1];
  }
  function setVersionLabel(version) {
    let label = state.getVersionLabelElement();
    if (!label) {
      label = document.getElementById("versionLabel");
      state.setVersionLabelElement(label);
    }
    if (label) label.textContent = version ? `namel3ss v${version}` : "";
  }
  utils.updateCopyButton = updateCopyButton;
  utils.showEmpty = showEmpty;
  utils.createCodeBlock = createCodeBlock;
  utils.setFileName = setFileName;
  utils.setVersionLabel = setVersionLabel;
  window.showEmpty = showEmpty;
})();
