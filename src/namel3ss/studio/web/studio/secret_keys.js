(() => {
  const root = window.N3Studio || (window.N3Studio = {});
  const secrets = root.secrets || (root.secrets = {});

  const PROVIDER_KEY_MAP = {
    openai: { canonical: "NAMEL3SS_OPENAI_API_KEY", alias: "OPENAI_API_KEY" },
    anthropic: { canonical: "NAMEL3SS_ANTHROPIC_API_KEY", alias: "ANTHROPIC_API_KEY" },
    gemini: {
      canonical: "NAMEL3SS_GEMINI_API_KEY",
      alias: "GEMINI_API_KEY",
      aliases: ["GOOGLE_API_KEY"],
    },
    mistral: { canonical: "NAMEL3SS_MISTRAL_API_KEY", alias: "MISTRAL_API_KEY" },
  };

  function normalizeProvider(value) {
    return String(value || "").trim().toLowerCase();
  }

  function getProviderKeys(provider) {
    return PROVIDER_KEY_MAP[normalizeProvider(provider)] || null;
  }

  function providerForKey(name) {
    const target = String(name || "").trim();
    if (!target) return null;
    return Object.keys(PROVIDER_KEY_MAP).find(
      (provider) => PROVIDER_KEY_MAP[provider].canonical === target
    ) || null;
  }

  function listProviderKeys(provider) {
    const keys = getProviderKeys(provider);
    if (!keys) return [];
    const list = [keys.canonical, keys.alias].concat(keys.aliases || []);
    return Array.from(new Set(list.filter(Boolean)));
  }

  function expandPlaceholders(provider, text) {
    if (typeof text !== "string") return text;
    const keys = getProviderKeys(provider);
    if (!keys) return text;
    return text
      .replace(/<CANONICAL_KEY>/g, keys.canonical)
      .replace(/<ALIAS_KEY>/g, keys.alias);
  }

  secrets.PROVIDER_KEY_MAP = PROVIDER_KEY_MAP;
  secrets.getProviderKeys = getProviderKeys;
  secrets.providerForKey = providerForKey;
  secrets.listProviderKeys = listProviderKeys;
  secrets.expandPlaceholders = expandPlaceholders;
})();
