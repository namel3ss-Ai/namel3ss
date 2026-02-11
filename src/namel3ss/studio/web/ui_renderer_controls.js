(() => {
  const root = window.N3UIRender || (window.N3UIRender = {});
  const sliderQueue = new Map();

  function renderSliderElement(el, handleAction) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-element ui-slider";
    const labelRow = document.createElement("div");
    labelRow.className = "ui-slider-label-row";

    const label = document.createElement("label");
    label.className = "ui-slider-label";
    label.textContent = typeof el.label === "string" ? el.label : "Slider";
    labelRow.appendChild(label);

    const valueBadge = document.createElement("span");
    valueBadge.className = "ui-slider-value";
    labelRow.appendChild(valueBadge);

    if (typeof el.help_tooltip_text === "string" && el.help_tooltip_text.trim()) {
      labelRow.appendChild(
        renderTooltipElement({
          type: "tooltip",
          text: el.help_tooltip_text,
          anchor_control_label: el.label || "",
          collapsed_by_default: true,
          inline: true,
        })
      );
    }
    wrapper.appendChild(labelRow);

    const error = document.createElement("div");
    error.className = "ui-slider-error";
    error.hidden = true;
    wrapper.appendChild(error);

    const input = document.createElement("input");
    input.type = "range";
    input.className = "ui-slider-input";
    input.min = String(toNumber(el.min, 0));
    input.max = String(toNumber(el.max, 1));
    input.step = String(Math.max(0.0001, toNumber(el.step, 0.1)));
    const currentValue = clamp(toNumber(el.value, Number(input.min)), Number(input.min), Number(input.max));
    input.value = String(currentValue);
    valueBadge.textContent = formatValue(currentValue);
    input.setAttribute("aria-label", label.textContent || "Slider");
    input.addEventListener("input", () => {
      valueBadge.textContent = formatValue(toNumber(input.value, currentValue));
    });
    input.addEventListener("change", async () => {
      const next = clamp(toNumber(input.value, currentValue), Number(input.min), Number(input.max));
      const action = normalizeAction(el);
      if (!action || typeof handleAction !== "function") {
        input.value = String(currentValue);
        valueBadge.textContent = formatValue(currentValue);
        showSliderError(error, "Unable to apply slider change.");
        return;
      }
      const ok = await queueSliderAction(action, next, handleAction, input);
      if (!ok) {
        input.value = String(currentValue);
        valueBadge.textContent = formatValue(currentValue);
        showSliderError(error, "Unable to apply slider change.");
      } else {
        hideSliderError(error);
        valueBadge.textContent = formatValue(next);
      }
    });
    wrapper.appendChild(input);
    return wrapper;
  }

  async function queueSliderAction(action, value, handleAction, source) {
    const key = String(action.id || action.flow || "slider");
    const previous = sliderQueue.get(key) || Promise.resolve(true);
    let resolveCurrent;
    const current = new Promise((resolve) => {
      resolveCurrent = resolve;
    });
    sliderQueue.set(
      key,
      previous
        .catch(() => true)
        .then(async () => {
          try {
            const payload = { [action.input_field || "value"]: value };
            const response = await handleAction(action, payload, source);
            resolveCurrent(!(response && response.ok === false));
          } catch (_err) {
            resolveCurrent(false);
          }
          return true;
        })
    );
    return current;
  }

  function normalizeAction(el) {
    const action = el && typeof el.action === "object" ? el.action : {};
    const actionId = typeof action.id === "string" && action.id ? action.id : typeof el.on_change_action === "string" ? el.on_change_action : "";
    const flow = typeof action.flow === "string" ? action.flow : "";
    if (!actionId || !flow) return null;
    return {
      id: actionId,
      type: "call_flow",
      flow: flow,
      input_field: typeof action.input_field === "string" && action.input_field ? action.input_field : "value",
    };
  }

  function renderTooltipElement(el) {
    const inline = Boolean(el && el.inline);
    const details = document.createElement("details");
    details.className = `ui-tooltip${inline ? " ui-tooltip-inline" : ""}`;
    const collapsed = !(el && el.collapsed_by_default === false);
    if (!collapsed) details.open = true;

    const summary = document.createElement("summary");
    summary.className = "ui-tooltip-summary";
    summary.textContent = inline ? "?" : "Help";
    details.appendChild(summary);

    const body = document.createElement("div");
    body.className = "ui-tooltip-body";
    body.textContent = typeof el.text === "string" ? el.text : "";
    if (!inline && typeof el.anchor_control_label === "string" && el.anchor_control_label) {
      const anchor = document.createElement("div");
      anchor.className = "ui-tooltip-anchor";
      anchor.textContent = `For: ${el.anchor_control_label}`;
      body.appendChild(anchor);
    }
    details.appendChild(body);
    return details;
  }

  function toNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function clamp(value, min, max) {
    if (value < min) return min;
    if (value > max) return max;
    return value;
  }

  function formatValue(value) {
    if (Math.abs(value - Math.round(value)) < 0.000001) return String(Math.round(value));
    return value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
  }

  function showSliderError(node, message) {
    if (!node) return;
    node.hidden = false;
    node.textContent = message;
  }

  function hideSliderError(node) {
    if (!node) return;
    node.hidden = true;
    node.textContent = "";
  }

  root.renderSliderElement = renderSliderElement;
  root.renderTooltipElement = renderTooltipElement;
})();
