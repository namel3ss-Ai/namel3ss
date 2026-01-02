(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const state = root.state;
  const preview = root.preview || (root.preview = {});

  let askActionId = null;
  let whyActionId = null;
  let isAsking = false;

  function getElements() {
    return {
      shell: document.getElementById("previewShell"),
      input: document.getElementById("previewQuestion"),
      askButton: document.getElementById("previewAsk"),
      answer: document.getElementById("previewAnswer"),
      whyButton: document.getElementById("previewWhy"),
      hint: document.getElementById("previewHint"),
    };
  }

  function setHint(text, isError) {
    const { hint } = getElements();
    if (!hint) return;
    hint.textContent = text || "";
    hint.classList.toggle("error", Boolean(isError));
  }

  function setAnswer(text, hasAnswer) {
    const { answer } = getElements();
    if (!answer) return;
    answer.textContent = text || "Ask a question to see an answer.";
    answer.classList.toggle("empty", !hasAnswer);
    setWhyVisible(hasAnswer);
  }

  function setWhyVisible(visible) {
    const { whyButton } = getElements();
    if (!whyButton) return;
    whyButton.classList.toggle("hidden", !visible);
    whyButton.disabled = !visible;
  }

  function setAskEnabled(enabled) {
    const { askButton } = getElements();
    if (!askButton) return;
    askButton.disabled = !enabled || isAsking;
  }

  function setAskLoading(loading) {
    isAsking = loading;
    const { askButton } = getElements();
    if (!askButton) return;
    askButton.textContent = loading ? "Asking..." : "Ask AI";
    askButton.disabled = loading || !askActionId;
  }

  function flattenElements(elements) {
    const list = [];
    (elements || []).forEach((element) => {
      list.push(element);
      if (Array.isArray(element.children)) {
        list.push(...flattenElements(element.children));
      }
    });
    return list;
  }

  function findTable(manifest, recordName) {
    if (!manifest || !manifest.pages) return null;
    for (const page of manifest.pages) {
      const elements = flattenElements(page.elements || []);
      for (const element of elements) {
        if (element.type === "table" && element.record === recordName) {
          return element;
        }
      }
    }
    return null;
  }

  function getAnswerText(manifest) {
    const table = findTable(manifest, "Answer");
    const rows = table && Array.isArray(table.rows) ? table.rows : [];
    if (!rows.length) return "";
    const row = rows[rows.length - 1] || {};
    const text = row.text;
    if (text && typeof text === "object") {
      if (typeof text.output === "string") return text.output;
      if (typeof text.output_text === "string") return text.output_text;
      try {
        return JSON.stringify(text);
      } catch (err) {
        return "";
      }
    }
    if (typeof text === "string") return text;
    return text ? String(text) : "";
  }

  function findActionIdByFlow(manifest, flowName) {
    const actions = manifest && manifest.actions ? Object.values(manifest.actions) : [];
    for (const action of actions) {
      if (!action || action.type !== "call_flow") continue;
      if (action.flow === flowName) return action.id || action.action_id || null;
    }
    return null;
  }

  function applyManifest(manifest) {
    askActionId = findActionIdByFlow(manifest, "ask_ai");
    whyActionId = findActionIdByFlow(manifest, "why_answer");
    setAskEnabled(Boolean(askActionId));
    const answer = getAnswerText(manifest);
    setAnswer(answer, Boolean(answer));
  }

  async function askQuestion() {
    const { input } = getElements();
    const question = input && input.value ? input.value.trim() : "";
    if (!question) {
      setHint("Ask a specific question to continue.", true);
      return;
    }
    if (!askActionId || !root.run || typeof root.run.executeAction !== "function") {
      setHint("Ask AI is unavailable in this app.", true);
      return;
    }
    setHint("", false);
    setAskLoading(true);
    try {
      const payload = { values: { question } };
      const result = await root.run.executeAction(askActionId, payload);
      const manifest = (result && result.ui) || state.getCachedManifest();
      if (manifest) applyManifest(manifest);
    } catch (err) {
      setAnswer("We could not answer that right now. Try again.", true);
    } finally {
      setAskLoading(false);
    }
  }

  async function runWhy() {
    if (!whyActionId || !root.run || typeof root.run.executeAction !== "function") {
      return;
    }
    setHint("Explanation updated.", false);
    await root.run.executeAction(whyActionId, {});
  }

  function renderError(detail) {
    const message = typeof detail === "string" ? detail : "Unable to load UI.";
    setHint(message, true);
    setAnswer("Ask a question to see an answer.", false);
  }

  function setupPreview() {
    const { askButton, input, whyButton } = getElements();
    if (askButton) askButton.addEventListener("click", () => askQuestion());
    if (input) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          askQuestion();
        }
      });
    }
    if (whyButton) whyButton.addEventListener("click", () => runWhy());
  }

  preview.applyManifest = applyManifest;
  preview.setupPreview = setupPreview;
  preview.renderError = renderError;
})();
