(() => {
  const root = window.N3App || (window.N3App = {});
  const utils = root.utils || (root.utils = {});
  function copyText(value) {
    if (!value && value !== "") return;
    const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).catch(() => {});
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
  }
  utils.copyText = copyText;
  window.copyText = copyText;
})();
