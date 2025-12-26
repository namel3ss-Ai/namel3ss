(() => {
  let overlayItems = [];
  let active = false;
  let mounted = [];

  function fetchOverlay() {
    return fetch("/learning_overlay.json")
      .then((res) => res.json())
      .then((data) => {
        overlayItems = Array.isArray(data.items) ? data.items : [];
      })
      .catch(() => {
        overlayItems = [];
      });
  }

  function toggleOverlay() {
    active = !active;
    const toggle = document.getElementById("learnToggle");
    if (toggle) toggle.setAttribute("aria-pressed", String(active));
    document.body.classList.toggle("learning-on", active);
    if (active) {
      mountTips();
    } else {
      clearTips();
    }
  }

  function mountTips() {
    clearTips();
    overlayItems.forEach((item) => {
      const target = document.querySelector(item.selector);
      if (!target) return;
      target.classList.add("learn-target");
      const tip = document.createElement("div");
      tip.className = "learn-tip";
      tip.innerHTML = `
        <div class="learn-title">${item.title}</div>
        <div class="learn-body">${item.body}</div>
        <a class="learn-link" href="${item.doc}" target="_blank">Read more</a>
      `;
      target.appendChild(tip);
      mounted.push({ target, tip });
    });
  }

  function clearTips() {
    mounted.forEach(({ target, tip }) => {
      target.classList.remove("learn-target");
      if (tip && tip.parentNode) tip.parentNode.removeChild(tip);
    });
    mounted = [];
  }

  function setupToggle() {
    const toggle = document.getElementById("learnToggle");
    if (!toggle) return;
    toggle.addEventListener("click", toggleOverlay);
  }

  fetchOverlay().then(setupToggle);
})();
