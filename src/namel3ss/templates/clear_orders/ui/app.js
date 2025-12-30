const state = {
  manifest: null,
  orders: [],
  answer: "",
  stats: [],
  whyOpen: false,
  asking: false,
  loadingWhy: false,
};

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
};

const ACTION_IDS = {
  seed: "page.home.button.seed_demo_data",
  ask: "page.home.button.ask_ai",
  why: "page.home.button.why",
};


function setHint(message, isError = false) {
  ELEMENTS.questionHint.textContent = message || "";
  ELEMENTS.questionHint.classList.toggle("error", isError);
}

function setAnswer(text, isEmpty = false) {
  ELEMENTS.answerText.textContent = text;
  ELEMENTS.answerText.classList.toggle("empty", isEmpty);
}

function setAskLoading(isLoading) {
  state.asking = isLoading;
  ELEMENTS.askButton.disabled = isLoading;
  ELEMENTS.askButton.textContent = isLoading ? "Asking..." : "Ask AI";
}

function setWhyLoading(isLoading) {
  state.loadingWhy = isLoading;
  ELEMENTS.whyButton.disabled = isLoading || !state.answer;
  ELEMENTS.whyButton.textContent = isLoading ? "Loading..." : "Why?";
}

function showOrdersLoading(show) {
  ELEMENTS.ordersLoading.style.display = show ? "block" : "none";
}

function showOrdersEmpty(show) {
  ELEMENTS.ordersEmpty.style.display = show ? "block" : "none";
}

function showWhyPlaceholder(show) {
  ELEMENTS.whyPlaceholder.style.display = show ? "block" : "none";
  ELEMENTS.whyList.style.display = show ? "none" : "block";
}

async function postAction(actionId, payload) {
  const res = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: actionId, payload: payload || {} }),
  });
  return res.json();
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
  const text = rows.length ? rows[rows.length - 1].text || "" : "";
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
  ELEMENTS.whyPanel.dataset.open = "true";
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

async function seedOrders() {
  showOrdersLoading(true);
  try {
    const data = await postAction(ACTION_IDS.seed, {});
    if (data && data.ui) {
      updateFromManifest(data.ui);
      return;
    }
    showOrdersLoading(false);
    showOrdersEmpty(true);
  } catch (err) {
    showOrdersLoading(false);
    showOrdersEmpty(true);
  }
}

async function askQuestion() {
  const question = ELEMENTS.questionInput.value.trim();
  if (question.length < 6) {
    setHint("Please ask a specific question about regions, returns, or delivery time.", true);
    return;
  }
  state.whyOpen = false;
  ELEMENTS.whyPanel.dataset.open = "false";
  showWhyPlaceholder(true);
  setHint("", false);
  setAskLoading(true);
  try {
    const data = await postAction(ACTION_IDS.ask, { values: { question } });
    if (!data || !data.ok) {
      setAnswer("We could not answer that right now. Try again.", false);
      return;
    }
    if (data.ui) {
      updateFromManifest(data.ui);
    }
  } catch (err) {
    setAnswer("We could not answer that right now. Try again.", false);
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
      updateFromManifest(data.ui);
    }
  } catch (err) {
    renderWhy([{ key: "fallback", value_text: "We could not build the full explanation, but the answer uses the orders shown here." }]);
  } finally {
    setWhyLoading(false);
  }
}

function bindEvents() {
  ELEMENTS.askButton.addEventListener("click", () => {
    askQuestion();
  });
  ELEMENTS.questionInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      askQuestion();
    }
  });
  ELEMENTS.whyButton.addEventListener("click", () => {
    showWhy();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  showOrdersLoading(true);
  showWhyPlaceholder(true);
  seedOrders();
});
