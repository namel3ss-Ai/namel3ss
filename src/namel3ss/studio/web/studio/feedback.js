(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const dom = root.dom;
  const net = root.net;
  const feedback = root.feedback || (root.feedback = {});

  let previewContext = null;
  let selectedRating = "";

  function getPreviewElements() {
    return {
      container: document.getElementById("previewFeedback"),
      ratings: Array.from(document.querySelectorAll(".preview-feedback-rating")),
      comment: document.getElementById("previewFeedbackComment"),
      submit: document.getElementById("previewFeedbackSubmit"),
      status: document.getElementById("previewFeedbackStatus"),
    };
  }

  function setPreviewStatus(text, isError) {
    const { status } = getPreviewElements();
    if (!status) return;
    status.textContent = text || "";
    status.classList.toggle("error", Boolean(isError));
  }

  function refreshRatingButtons() {
    const { ratings } = getPreviewElements();
    ratings.forEach((button) => {
      const match = button.dataset.rating === selectedRating;
      button.classList.toggle("active", match);
      button.setAttribute("aria-pressed", match ? "true" : "false");
    });
  }

  function setPreviewContext(context) {
    previewContext = context || null;
    selectedRating = "";
    const { container, comment } = getPreviewElements();
    if (comment) comment.value = "";
    refreshRatingButtons();
    setPreviewStatus("", false);
    if (container) {
      container.classList.toggle("hidden", !previewContext);
    }
  }

  async function submitPreviewFeedback() {
    const { comment } = getPreviewElements();
    if (!previewContext) {
      setPreviewStatus("Run Ask AI first.", true);
      return;
    }
    if (!selectedRating) {
      setPreviewStatus("Choose a rating first.", true);
      return;
    }
    try {
      await net.postJson("/api/feedback", {
        flow_name: previewContext.flow_name,
        input_text: previewContext.input_text,
        input_id: previewContext.input_id,
        rating: selectedRating,
        comment: comment && comment.value ? comment.value.trim() : "",
      });
      setPreviewStatus("Feedback saved.", false);
      await renderFeedback();
    } catch (err) {
      setPreviewStatus(err && err.message ? err.message : "Feedback failed.", true);
    }
  }

  function setupPreviewFeedback() {
    const { ratings, submit } = getPreviewElements();
    ratings.forEach((button) => {
      button.addEventListener("click", () => {
        selectedRating = button.dataset.rating || "";
        refreshRatingButtons();
        setPreviewStatus("", false);
      });
    });
    if (submit) {
      submit.addEventListener("click", () => submitPreviewFeedback());
    }
  }

  function buildSummaryCard(title, lines) {
    const section = document.createElement("div");
    section.className = "panel-section";
    const heading = document.createElement("div");
    heading.className = "panel-section-title";
    heading.textContent = title;
    section.appendChild(heading);
    const stack = document.createElement("div");
    stack.className = "status-lines";
    (lines || []).forEach((line) => {
      const row = document.createElement("div");
      row.className = "status-line";
      row.textContent = line;
      stack.appendChild(row);
    });
    section.appendChild(stack);
    return section;
  }

  function buildEntriesList(entries) {
    const section = document.createElement("div");
    section.className = "panel-section";
    const heading = document.createElement("div");
    heading.className = "panel-section-title";
    heading.textContent = "Recent feedback";
    section.appendChild(heading);

    if (!entries.length) {
      section.appendChild(dom.buildEmpty("No feedback entries yet."));
      return section;
    }

    const list = document.createElement("div");
    list.className = "list";
    entries.slice(-20).reverse().forEach((entry) => {
      const row = document.createElement("div");
      row.className = "list-item";
      const comment = entry.comment ? ` comment=${entry.comment}` : "";
      row.textContent = `step=${entry.step_count} flow=${entry.flow_name} rating=${entry.rating}${comment}`;
      list.appendChild(row);
    });
    section.appendChild(list);
    return section;
  }

  async function renderFeedback() {
    const panel = document.getElementById("feedback");
    if (!panel) return;
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";
    wrapper.appendChild(dom.buildEmpty("Loading feedback..."));
    panel.appendChild(wrapper);

    try {
      const [feedbackPayload, retrainPayload, canaryPayload] = await Promise.all([
        net.fetchJson("/api/feedback"),
        net.fetchJson("/api/retrain"),
        net.fetchJson("/api/canary"),
      ]);

      panel.innerHTML = "";
      const layout = document.createElement("div");
      layout.className = "panel-stack";

      const summary = feedbackPayload && feedbackPayload.summary ? feedbackPayload.summary : {};
      layout.appendChild(
        buildSummaryCard("Feedback summary", [
          `total ${summary.total || 0}`,
          `excellent ${summary.excellent || 0}`,
          `good ${summary.good || 0}`,
          `bad ${summary.bad || 0}`,
          `positive ratio ${(summary.positive_ratio || 0).toFixed ? summary.positive_ratio.toFixed(3) : summary.positive_ratio}`,
        ])
      );

      const retrainSuggestions = retrainPayload && Array.isArray(retrainPayload.suggestions) ? retrainPayload.suggestions : [];
      const canaryRows = canaryPayload && Array.isArray(canaryPayload.summary) ? canaryPayload.summary : [];

      layout.appendChild(
        buildSummaryCard("Retrain", [
          `suggestions ${retrainSuggestions.length}`,
          retrainSuggestions.length ? String(retrainSuggestions[0].reason || "") : "No thresholds triggered.",
        ])
      );

      layout.appendChild(
        buildSummaryCard("Canary", [
          `comparisons ${canaryRows.length}`,
          canaryRows.length ? `${canaryRows[0].primary_model} vs ${canaryRows[0].candidate_model}` : "No canary records yet.",
        ])
      );

      const scheduleRow = document.createElement("div");
      scheduleRow.className = "panel-section";
      const scheduleTitle = document.createElement("div");
      scheduleTitle.className = "panel-section-title";
      scheduleTitle.textContent = "Actions";
      const scheduleBtn = document.createElement("button");
      scheduleBtn.className = "btn ghost";
      scheduleBtn.textContent = "Schedule retrain";
      const scheduleStatus = document.createElement("div");
      scheduleStatus.className = "preview-hint";
      scheduleBtn.addEventListener("click", async () => {
        scheduleBtn.disabled = true;
        scheduleBtn.textContent = "Scheduling...";
        try {
          const resp = await net.postJson("/api/retrain/schedule", {});
          const count = resp && Array.isArray(resp.suggestions) ? resp.suggestions.length : 0;
          scheduleStatus.textContent = `Saved ${count} retrain suggestion(s).`;
        } catch (err) {
          scheduleStatus.textContent = err && err.message ? err.message : "Could not schedule retrain.";
          scheduleStatus.classList.add("error");
        } finally {
          scheduleBtn.disabled = false;
          scheduleBtn.textContent = "Schedule retrain";
          renderFeedback();
        }
      });
      scheduleRow.appendChild(scheduleTitle);
      scheduleRow.appendChild(scheduleBtn);
      scheduleRow.appendChild(scheduleStatus);
      layout.appendChild(scheduleRow);

      const entries = feedbackPayload && Array.isArray(feedbackPayload.entries) ? feedbackPayload.entries : [];
      layout.appendChild(buildEntriesList(entries));

      panel.appendChild(layout);
    } catch (err) {
      panel.innerHTML = "";
      dom.showError(panel, err && err.message ? err.message : "Feedback panel failed to load.");
    }
  }

  feedback.setupPreviewFeedback = setupPreviewFeedback;
  feedback.setPreviewContext = setPreviewContext;
  feedback.renderFeedback = renderFeedback;
})();
