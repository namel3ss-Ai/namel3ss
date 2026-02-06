(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const net = root.net;
  const playground = root.playground || (root.playground = {});

  async function callPlayground(action, source, inputPayload) {
    const body = { action, source };
    if (inputPayload) body.input = inputPayload;
    return net.postJson("/api/playground", body);
  }

  function defaultSnippet() {
    return [
      'spec is "1.0"',
      "",
      'contract flow "hello":',
      "  input:",
      "    name is text",
      "  output:",
      "    greeting is text",
      "",
      'flow "hello": purity is "pure"',
      '  return "hello" + " " + input.name',
      "",
    ].join("\n");
  }

  async function renderPlayground() {
    const panel = document.getElementById("playground");
    if (!panel) return;
    panel.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.className = "panel-stack";

    const section = document.createElement("div");
    section.className = "panel-section";
    const title = document.createElement("div");
    title.className = "panel-section-title";
    title.textContent = "Playground";
    section.appendChild(title);

    const source = document.createElement("textarea");
    source.rows = 16;
    source.className = "code-block";
    source.value = defaultSnippet();
    section.appendChild(source);

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = 'Run input JSON, for example {"name":"Ada"}';
    section.appendChild(input);

    const controls = document.createElement("div");
    controls.className = "ui-buttons";

    const checkBtn = document.createElement("button");
    checkBtn.className = "btn ghost";
    checkBtn.textContent = "Check";
    controls.appendChild(checkBtn);

    const runBtn = document.createElement("button");
    runBtn.className = "btn primary";
    runBtn.textContent = "Run";
    controls.appendChild(runBtn);

    section.appendChild(controls);

    const status = document.createElement("div");
    status.className = "preview-hint";
    section.appendChild(status);

    const output = document.createElement("pre");
    output.className = "code-block";
    output.textContent = "";
    section.appendChild(output);

    wrapper.appendChild(section);
    panel.appendChild(wrapper);

    checkBtn.addEventListener("click", async () => {
      try {
        const payload = await callPlayground("check", source.value, null);
        status.classList.toggle("error", !payload.ok);
        status.textContent = payload.ok
          ? `Valid snippet. Flows: ${(payload.flows || []).join(", ")}`
          : (payload.error || "Snippet has errors.");
        output.textContent = JSON.stringify(payload, null, 2);
      } catch (err) {
        status.classList.add("error");
        status.textContent = err && err.message ? err.message : "Check failed.";
      }
    });

    runBtn.addEventListener("click", async () => {
      let parsedInput = null;
      if (input.value.trim()) {
        try {
          parsedInput = JSON.parse(input.value);
        } catch (_err) {
          status.classList.add("error");
          status.textContent = "Input must be valid JSON.";
          return;
        }
      }
      try {
        const payload = await callPlayground("run", source.value, parsedInput);
        status.classList.toggle("error", !payload.ok);
        status.textContent = payload.ok
          ? `Ran flow ${payload.flow_name || "unknown"}.`
          : (payload.error || "Run failed.");
        output.textContent = JSON.stringify(payload, null, 2);
      } catch (err) {
        status.classList.add("error");
        status.textContent = err && err.message ? err.message : "Run failed.";
      }
    });
  }

  playground.renderPlayground = renderPlayground;
})();
