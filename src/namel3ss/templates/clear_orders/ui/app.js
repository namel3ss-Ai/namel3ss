const state = {
  manifest: null,
  orders: [],
  answer: "",
  stats: [],
  whyOpen: false,
  asking: false,
  loadingWhy: false,
};

const UI_ERROR_MESSAGE = "Couldn't update the page. Try again.";

const ELEMENTS = {
  ordersBody: document.getElementById("ordersBody"),
  ordersLoading: document.getElementById("ordersLoading"),
  ordersEmpty: document.getElementById("ordersEmpty"),
  questionInput: document.getElementById("questionInput"),
  askButton: document.getElementById("askButton"),
  questionHint: document.getElementById("questionHint"),
  answerText: document.getElementById("answerText"),
  whyButton: document.getElementById("whyButton"),
  whyPanel: document.getElementById("whyPanel"),
  whyList: document.getElementById("whyList"),
  whyPlaceholder: document.getElementById("whyPlaceholder"),
  aiModeValue: document.getElementById("aiModeValue"),
  aiProviderValue: document.getElementById("aiProviderValue"),
  aiModeHint: document.getElementById("aiModeHint"),
};

const ACTION_IDS = {
  seed: "page.home.button.seed_demo_data",
  ask: "page.home.button.ask_ai",
  why: "page.home.button.why",
};

const DEFAULT_PAGE = "intro";

function safeSetText(element, text) {
  if (!element) return false;
  element.textContent = text;
  return true;
}

function safeToggleClass(element, className, enabled) {
  if (!element) return false;
  element.classList.toggle(className, enabled);
  return true;
}

function safeSetDisplay(element, show) {
  if (!element) return false;
  element.style.display = show ? "block" : "none";
  return true;
}

function safeSetDisabled(element, disabled) {
  if (!element) return false;
  element.disabled = disabled;
  return true;
}

function safeSetDataset(element, key, value) {
  if (!element) return false;
  element.dataset[key] = value;
  return true;
}

function logUpdateError(context, err) {
  console.error(`[ClearOrders] ${context}`, err);
}

function setHint(message, isError = false) {
  safeSetText(ELEMENTS.questionHint, message || "");
  safeToggleClass(ELEMENTS.questionHint, "error", isError);
}

function setAnswer(text, isEmpty = false) {
  safeSetText(ELEMENTS.answerText, text);
  safeToggleClass(ELEMENTS.answerText, "empty", isEmpty);
}

function applyStatusMessage(status) {
  const message = status && status.message ? status.message : "";
  if (message) {
    setHint(message, true);
    return;
  }
  setHint("", false);
}

function formatAiMode(state) {
  const mode = state && state.ai_mode ? String(state.ai_mode) : "mock";
  const provider = state && state.ai_provider_selected ? String(state.ai_provider_selected) : "assistant";
  const label = mode === "real" && provider === "assistant_openai" ? "OpenAI" : "Mock";
  return { mode, provider, label };
}

function applyAiMode(stateData) {
  const info = formatAiMode(stateData || {});
  safeSetText(ELEMENTS.aiModeValue, info.label);
  safeSetText(ELEMENTS.aiProviderValue, info.provider);
  if (info.label === "Mock") {
    safeSetText(
      ELEMENTS.aiModeHint,
      "Add NAMEL3SS_OPENAI_API_KEY or OPENAI_API_KEY and refresh."
    );
  } else {
    safeSetText(ELEMENTS.aiModeHint, "");
  }
}

function showAnswerError() {
  setAnswer(UI_ERROR_MESSAGE, false);
}

function setAskLoading(isLoading) {
  state.asking = isLoading;
  safeSetDisabled(ELEMENTS.askButton, isLoading);
  safeSetText(ELEMENTS.askButton, isLoading ? "Asking..." : "Ask AI");
}

function setWhyLoading(isLoading) {
  state.loadingWhy = isLoading;
  safeSetDisabled(ELEMENTS.whyButton, isLoading || !state.answer);
  safeSetText(ELEMENTS.whyButton, isLoading ? "Loading..." : "Why?");
}

function showOrdersLoading(show) {
  safeSetDisplay(ELEMENTS.ordersLoading, show);
}

function showOrdersEmpty(show) {
  safeSetDisplay(ELEMENTS.ordersEmpty, show);
}

function showWhyPlaceholder(show) {
  safeSetDisplay(ELEMENTS.whyPlaceholder, show);
  safeSetDisplay(ELEMENTS.whyList, !show);
}

async function postAction(actionId, payload) {
  if (typeof fetch !== "function") {
    throw new Error("Fetch is unavailable in this environment.");
  }
  const res = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: actionId, payload: payload || {} }),
  });
  try {
    return await res.json();
  } catch (err) {
    throw new Error("Unable to parse the response.");
  }
}

function flattenElements(elements) {
  const list = [];
  (elements || []).forEach((element) => {
    list.push(element);
    if (element.children) {
      list.push(...flattenElements(element.children));
    }
  });
  return list;
}

function findTableRows(manifest, recordName) {
  if (!manifest || !manifest.pages) return [];
  for (const page of manifest.pages) {
    const elements = flattenElements(page.elements || []);
    for (const element of elements) {
      if (element.type === "table" && element.record === recordName) {
        return element.rows || [];
      }
    }
  }
  return [];
}

function renderOrders(rows) {
  state.orders = rows || [];
  if (!ELEMENTS.ordersBody) return;
  ELEMENTS.ordersBody.innerHTML = "";
  showOrdersLoading(false);
  if (!rows || rows.length === 0) {
    showOrdersEmpty(true);
    return;
  }
  showOrdersEmpty(false);
  const frag = document.createDocumentFragment();
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.order_id || ""}</td>
      <td>${row.customer || ""}</td>
      <td>${row.region || ""}</td>
      <td>${row.segment || ""}</td>
      <td>${formatMoney(row.total_usd)}</td>
      <td>${row.shipping || ""}</td>
      <td>${row.delivery_days ?? ""}</td>
      <td>${row.returned ? "Yes" : "No"}</td>
      <td>${row.satisfaction ?? ""}</td>
      <td>${row.order_date || ""}</td>
      <td>${row.return_reason || ""}</td>
    `;
    frag.appendChild(tr);
  });
  ELEMENTS.ordersBody.appendChild(frag);
}

function renderAnswer(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const text = list.length ? list[list.length - 1].text || "" : "";
  state.answer = text.trim();
  if (!state.answer) {
    setAnswer("Ask a question to see an answer.", true);
  } else {
    setAnswer(state.answer, false);
  }
  setWhyLoading(state.loadingWhy);
}

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "";
  const number = Number(value);
  if (Number.isNaN(number)) return value;
  return `$${number.toFixed(0)}`;
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  if (Number.isNaN(number)) return null;
  return number.toFixed(1).replace(/\.0$/, "");
}

function buildBullets(stats) {
  const map = {};
  stats.forEach((stat) => {
    if (stat.key) map[stat.key] = stat;
  });
  const bullets = [];
  const orders = map.orders_reviewed ? map.orders_reviewed.value_number : null;
  const topRegion = map.top_region ? map.top_region.value_text : null;
  const topReturns = map.top_region_returns ? map.top_region_returns.value_number : null;
  const avgDelivery = map.avg_delivery_days ? formatNumber(map.avg_delivery_days.value_number) : null;
  const avgSatisfaction = map.avg_satisfaction ? formatNumber(map.avg_satisfaction.value_number) : null;
  const fallbackText = map.fallback ? map.fallback.value_text : null;

  if (orders !== null) {
    bullets.push(`Reviewed ${orders} orders to answer your question.`);
  }
  if (topRegion && topReturns !== null) {
    bullets.push(`Highest returns are in ${topRegion} with ${topReturns} returns.`);
  }
  if (avgDelivery !== null) {
    bullets.push(`Average delivery time on returned orders is ${avgDelivery} days.`);
  }
  if (avgSatisfaction !== null) {
    bullets.push(`Average satisfaction on returned orders is ${avgSatisfaction} out of 5.`);
  }
  if (fallbackText) {
    bullets.unshift(fallbackText);
  }

  const defaults = [
    "The answer is based on the orders shown on this page.",
    "Returns and delivery time patterns shape the summary.",
    "The data highlights where returns cluster most often.",
  ];

  for (const line of defaults) {
    if (bullets.length >= 3) break;
    bullets.push(line);
  }

  return bullets.slice(0, 5);
}

function renderWhy(stats) {
  state.stats = stats || [];
  if (!ELEMENTS.whyList || !ELEMENTS.whyPanel) return;
  const bullets = buildBullets(state.stats);
  ELEMENTS.whyList.innerHTML = "";
  if (!state.whyOpen) {
    showWhyPlaceholder(true);
    return;
  }
  showWhyPlaceholder(false);
  const frag = document.createDocumentFragment();
  bullets.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    frag.appendChild(li);
  });
  ELEMENTS.whyList.appendChild(frag);
  safeSetDataset(ELEMENTS.whyPanel, "open", "true");
}

function updateFromManifest(manifest) {
  state.manifest = manifest;
  const orders = findTableRows(manifest, "Order");
  const answers = findTableRows(manifest, "Answer");
  const stats = findTableRows(manifest, "ExplanationStat");
  renderOrders(orders);
  renderAnswer(answers);
  renderWhy(stats);
}

function applyManifest(manifest, context) {
  if (!manifest) return false;
  try {
    updateFromManifest(manifest);
    return true;
  } catch (err) {
    logUpdateError(`${context} update failed`, err);
    showAnswerError();
    return false;
  }
}

async function seedOrders() {
  showOrdersLoading(true);
  try {
    const data = await postAction(ACTION_IDS.seed, {});
    if (data && data.ui) {
      applyManifest(data.ui, "seed");
      applyAiMode(data.state);
      return;
    }
    showOrdersLoading(false);
    showOrdersEmpty(true);
  } catch (err) {
    logUpdateError("seed request failed", err);
    showOrdersLoading(false);
    showOrdersEmpty(true);
  }
}

async function askQuestion() {
  if (!ELEMENTS.questionInput) {
    logUpdateError("question input missing", new Error("Input not found"));
    showAnswerError();
    return;
  }
  const question = ELEMENTS.questionInput.value.trim();
  if (question.length < 6) {
    setHint("Please ask a specific question about regions, returns, or delivery time.", true);
    return;
  }
  state.whyOpen = false;
  safeSetDataset(ELEMENTS.whyPanel, "open", "false");
  showWhyPlaceholder(true);
  setHint("", false);
  setAskLoading(true);
  try {
    const data = await postAction(ACTION_IDS.ask, { values: { question } });
    if (!data || !data.ok) {
      showAnswerError();
      return;
    }
    const nextManifest = data.ui || state.manifest;
    if (nextManifest) {
      applyManifest(nextManifest, "ask");
      applyStatusMessage(data.state ? data.state.status : null);
      applyAiMode(data.state);
    } else {
      showAnswerError();
    }
  } catch (err) {
    logUpdateError("ask request failed", err);
    showAnswerError();
  } finally {
    setAskLoading(false);
    setWhyLoading(false);
  }
}

async function showWhy() {
  state.whyOpen = true;
  setWhyLoading(true);
  try {
    const data = await postAction(ACTION_IDS.why, {});
    if (data && data.ui) {
      applyManifest(data.ui, "why");
      applyAiMode(data.state);
    }
  } catch (err) {
    logUpdateError("why request failed", err);
    renderWhy([{ key: "fallback", value_text: "We could not build the full explanation, but the answer uses the orders shown here." }]);
  } finally {
    setWhyLoading(false);
  }
}

function bindEvents() {
  if (ELEMENTS.askButton) {
    ELEMENTS.askButton.addEventListener("click", () => {
      askQuestion();
    });
  }
  if (ELEMENTS.questionInput) {
    ELEMENTS.questionInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        askQuestion();
      }
    });
  }
  if (ELEMENTS.whyButton) {
    ELEMENTS.whyButton.addEventListener("click", () => {
      showWhy();
    });
  }
}

function setActivePage(name) {
  const pages = document.querySelectorAll(".page-view");
  let matched = false;
  pages.forEach((page) => {
    const isActive = page.dataset.page === name;
    page.classList.toggle("is-active", isActive);
    if (isActive) matched = true;
  });
  if (!matched && pages.length) {
    pages[0].classList.add("is-active");
  }
}

function bindNavigation() {
  const buttons = document.querySelectorAll("[data-nav]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const target = button.dataset.nav;
      if (target) {
        setActivePage(target);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setActivePage(DEFAULT_PAGE);
  bindNavigation();
  bindEvents();
  showOrdersLoading(true);
  showWhyPlaceholder(true);
  seedOrders();
});
