(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const guidance = root.guidance || (root.guidance = {});

  const LABELS = {
    "what happened": "what",
    "why": "why",
    "fix": "fix",
    "how to fix": "fix",
    "where": "where",
    "example": "example",
    "try": "example",
  };

  function parseGuidance(text) {
    const raw = typeof text === "string" ? text : "";
    const result = { raw, what: "", why: "", fix: "", where: "", example: "" };
    if (!raw) return result;

    let normalized = raw.replace(/\s+\|\s+/g, "\n");
    Object.keys(LABELS).forEach((label) => {
      const pattern = new RegExp(`\\b${label}\\s*[:\\-]\\s*`, "gi");
      normalized = normalized.replace(pattern, `\n${label}: `);
    });

    const sections = { what: [], why: [], fix: [], where: [], example: [] };
    let current = "";
    normalized.split(/\r?\n/).forEach((line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      const match = trimmed.match(/^([A-Za-z ]+)\s*:\s*(.*)$/);
      if (match) {
        const key = match[1].toLowerCase();
        const target = LABELS[key];
        if (target) {
          current = target;
          if (match[2]) sections[target].push(match[2]);
          return;
        }
      }
      if (current) {
        sections[current].push(trimmed);
      }
    });

    Object.keys(sections).forEach((key) => {
      if (sections[key].length) {
        result[key] = sections[key].join(" ").trim();
      }
    });
    return result;
  }

  guidance.parseGuidance = parseGuidance;
})();
