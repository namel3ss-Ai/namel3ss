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
      feedback: document.getElementById("previewFeedback"),
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
    setFeedbackVisible(hasAnswer);
  }

  function setWhyVisible(visible) {
    const { whyButton } = getElements();
    if (!whyButton) return;
    whyButton.classList.toggle("hidden", !visible);
    whyButton.disabled = !visible;
  }

  function setFeedbackVisible(visible) {
    const { feedback } = getElements();
    if (!feedback) return;
    feedback.classList.toggle("hidden", !visible);
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
    askButton.textContent = loading ? "Stop" : "Ask AI";
    askButton.disabled = !askActionId;
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
    let streamAnswer = "";
    setAnswer("Thinking...", false);
    try {
      const payload = { values: { question } };
      const result = await root.run.executeAction(askActionId, payload, {
        stream: true,
        onStreamEvent: (event) => {
          const eventType = event && event.event ? event.event : "";
          const data = event && event.data && typeof event.data === "object" ? event.data : null;
          if (!data) return;
          if (eventType === "token" && typeof data.output === "string") {
            streamAnswer += data.output;
            setAnswer(streamAnswer, Boolean(streamAnswer));
            return;
          }
          if (eventType === "finish" && typeof data.output === "string") {
            streamAnswer = data.output;
            setAnswer(streamAnswer, Boolean(streamAnswer));
          }
        },
      });
      if (result && result.cancelled) {
        setHint("Streaming cancelled.", true);
        return;
      }
      const manifest = (result && result.ui) || state.getCachedManifest();
      if (manifest) applyManifest(manifest);
      if (root.feedback && typeof root.feedback.setPreviewContext === "function") {
        root.feedback.setPreviewContext({ flow_name: "ask_ai", input_text: question });
      }
    } catch (err) {
      setAnswer("We could not answer that right now. Try again.", true);
      if (root.feedback && typeof root.feedback.setPreviewContext === "function") {
        root.feedback.setPreviewContext(null);
      }
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
    if (askButton) {
      askButton.addEventListener("click", () => {
        if (isAsking && root.run && typeof root.run.cancelActiveAction === "function") {
          root.run.cancelActiveAction();
          return;
        }
        askQuestion();
      });
    }
    if (input) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          if (!isAsking) askQuestion();
        }
      });
    }
    if (whyButton) whyButton.addEventListener("click", () => runWhy());
  }

  preview.applyManifest = applyManifest;
  preview.setupPreview = setupPreview;
  preview.renderError = renderError;
})();
