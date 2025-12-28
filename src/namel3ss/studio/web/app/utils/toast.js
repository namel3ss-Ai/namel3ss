(() => {
  const root = window.N3App || (window.N3App = {});
  const utils = root.utils || (root.utils = {});
  function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.style.display = "block";
    setTimeout(() => {
      toast.style.display = "none";
    }, 2000);
  }
  utils.showToast = showToast;
  window.showToast = showToast;
})();
