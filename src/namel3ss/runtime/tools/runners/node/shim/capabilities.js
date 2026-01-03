"use strict";

const { installPatches } = require("./patches");

const CAPABILITY_TO_GUARANTEE = {
  filesystem_read: "no_filesystem_read",
  filesystem_write: "no_filesystem_write",
  network: "no_network",
  subprocess: "no_subprocess",
  env_read: "no_env_read",
  env_write: "no_env_write",
  secrets: "secrets_allowed",
};

const SECRET_ALIASES = {
  NAMEL3SS_OPENAI_API_KEY: "OPENAI_API_KEY",
  OPENAI_API_KEY: "OPENAI_API_KEY",
  NAMEL3SS_ANTHROPIC_API_KEY: "ANTHROPIC_API_KEY",
  ANTHROPIC_API_KEY: "ANTHROPIC_API_KEY",
  NAMEL3SS_GEMINI_API_KEY: "GEMINI_API_KEY",
  GEMINI_API_KEY: "GEMINI_API_KEY",
  NAMEL3SS_MISTRAL_API_KEY: "MISTRAL_API_KEY",
  MISTRAL_API_KEY: "MISTRAL_API_KEY",
  N3_DATABASE_URL: "DATABASE_URL",
  DATABASE_URL: "DATABASE_URL",
  N3_EDGE_KV_URL: "EDGE_KV_URL",
  EDGE_KV_URL: "EDGE_KV_URL",
};

const REASON_GUARANTEE_ALLOWED = "guarantee_allowed";
const REASON_GUARANTEE_BLOCKED = "guarantee_blocked";
const REASON_SECRETS_ALLOWED = "secrets_allowed";
const REASON_SECRETS_BLOCKED = "secrets_blocked";

let capabilityContext = null;
let capabilityChecks = [];
let allowedEmitted = new Set();

class CapabilityViolation extends Error {
  constructor(message, check) {
    super(message);
    this.name = "CapabilityViolation";
    this.check = check;
  }
}

function configureCapabilities(payload) {
  capabilityChecks = [];
  allowedEmitted = new Set();
  const context = payload && payload.capability_context;
  if (!context || typeof context !== "object") {
    capabilityContext = null;
    return;
  }
  capabilityContext = normalizeCapabilityContext(context, payload);
  installPatches({
    guardFilesystem,
    guardNetwork,
    guardEnvRead,
    guardEnvWrite,
    guardSubprocess,
  });
}

function getCapabilityChecks() {
  return capabilityChecks;
}

function normalizeCapabilityContext(context, payload) {
  const rawGuarantees =
    context && typeof context.guarantees === "object" && context.guarantees ? context.guarantees : {};
  const rawSources = context && typeof context.sources === "object" && context.sources ? context.sources : {};
  return {
    toolName: String(context.tool_name || payload.tool || payload.tool_name || "tool"),
    resolvedSource: String(context.resolved_source || "binding"),
    runner: String(context.runner || "node"),
    protocolVersion: Number(context.protocol_version || 1),
    guarantees: {
      no_filesystem_write: Boolean(rawGuarantees.no_filesystem_write),
      no_filesystem_read: Boolean(rawGuarantees.no_filesystem_read),
      no_network: Boolean(rawGuarantees.no_network),
      no_subprocess: Boolean(rawGuarantees.no_subprocess),
      no_env_read: Boolean(rawGuarantees.no_env_read),
      no_env_write: Boolean(rawGuarantees.no_env_write),
      secrets_allowed: Array.isArray(rawGuarantees.secrets_allowed)
        ? rawGuarantees.secrets_allowed.map((item) => String(item))
        : null,
    },
    sources: rawSources,
  };
}

function sourceFor(capability) {
  if (!capabilityContext) {
    return "pack";
  }
  const key = CAPABILITY_TO_GUARANTEE[capability];
  if (!key) {
    return "pack";
  }
  const source = capabilityContext.sources && capabilityContext.sources[key];
  if (typeof source === "string" && source) {
    return source;
  }
  return "pack";
}

function recordCheck(check) {
  if (!capabilityContext) {
    return;
  }
  if (check.allowed && allowedEmitted.has(check.capability)) {
    return;
  }
  if (check.allowed) {
    allowedEmitted.add(check.capability);
  }
  capabilityChecks.push(check);
}

function buildCheck(capability, allowed, reason) {
  return {
    capability: String(capability),
    allowed: Boolean(allowed),
    guarantee_source: sourceFor(capability),
    reason: String(reason),
  };
}

function buildBlockMessage(toolName, action, why, example) {
  return [
    `What happened: Tool "${toolName}" ${action}.`,
    `Why: ${why}`,
    "Fix: Remove the restriction or choose a tool that does not need the capability.",
    `Example: ${example}`,
  ].join("\n");
}

function normalizeSecretName(name) {
  if (!name) {
    return null;
  }
  const key = String(name).trim().toUpperCase();
  return SECRET_ALIASES[key] || null;
}

function guardNetwork(url, method) {
  if (!capabilityContext) {
    return;
  }
  if (!capabilityContext.guarantees.no_network) {
    recordCheck(buildCheck("network", true, REASON_GUARANTEE_ALLOWED));
    return;
  }
  const check = buildCheck("network", false, REASON_GUARANTEE_BLOCKED);
  recordCheck(check);
  const toolName = capabilityContext.toolName;
  const action = "cannot access the network";
  const why = `Effective guarantees forbid network access (${method} ${String(url)}).`;
  const example = `[capability_overrides]\n"${toolName}" = { no_network = true }`;
  throw new CapabilityViolation(buildBlockMessage(toolName, action, why, example), check);
}

function guardFilesystem(pathValue, mode) {
  if (!capabilityContext) {
    return;
  }
  const write = isWriteMode(mode);
  const capability = write ? "filesystem_write" : "filesystem_read";
  const deny = write
    ? capabilityContext.guarantees.no_filesystem_write
    : capabilityContext.guarantees.no_filesystem_read;
  if (!deny) {
    recordCheck(buildCheck(capability, true, REASON_GUARANTEE_ALLOWED));
    return;
  }
  const check = buildCheck(capability, false, REASON_GUARANTEE_BLOCKED);
  recordCheck(check);
  const toolName = capabilityContext.toolName;
  const target = String(pathValue);
  const action = write ? "cannot write to the filesystem" : "cannot read from the filesystem";
  const why = `Effective guarantees forbid filesystem access (${target}).`;
  const example = `[capability_overrides]\n"${toolName}" = { no_filesystem_write = true }`;
  throw new CapabilityViolation(buildBlockMessage(toolName, action, why, example), check);
}

function guardEnvRead(key) {
  if (!capabilityContext) {
    return;
  }
  if (!capabilityContext.guarantees.no_env_read) {
    recordCheck(buildCheck("env_read", true, REASON_GUARANTEE_ALLOWED));
  } else {
    const check = buildCheck("env_read", false, REASON_GUARANTEE_BLOCKED);
    recordCheck(check);
    const toolName = capabilityContext.toolName;
    const action = "cannot read environment variables";
    const why = `Effective guarantees forbid env reads (${String(key)}).`;
    const example = `[capability_overrides]\n"${toolName}" = { no_env_read = true }`;
    throw new CapabilityViolation(buildBlockMessage(toolName, action, why, example), check);
  }
  const secretName = normalizeSecretName(key);
  if (secretName) {
    guardSecretAllowed(secretName);
  }
}

function guardEnvWrite(key) {
  if (!capabilityContext) {
    return;
  }
  if (!capabilityContext.guarantees.no_env_write) {
    recordCheck(buildCheck("env_write", true, REASON_GUARANTEE_ALLOWED));
  } else {
    const check = buildCheck("env_write", false, REASON_GUARANTEE_BLOCKED);
    recordCheck(check);
    const toolName = capabilityContext.toolName;
    const action = "cannot write environment variables";
    const why = `Effective guarantees forbid env writes (${String(key)}).`;
    const example = `[capability_overrides]\n"${toolName}" = { no_env_write = true }`;
    throw new CapabilityViolation(buildBlockMessage(toolName, action, why, example), check);
  }
  const secretName = normalizeSecretName(key);
  if (secretName) {
    guardSecretAllowed(secretName);
  }
}

function guardSecretAllowed(secretName) {
  if (!capabilityContext) {
    return;
  }
  const allowed = capabilityContext.guarantees.secrets_allowed;
  if (!Array.isArray(allowed)) {
    recordCheck(buildCheck("secrets", true, REASON_GUARANTEE_ALLOWED));
    return;
  }
  if (allowed.includes(secretName)) {
    recordCheck(buildCheck("secrets", true, REASON_SECRETS_ALLOWED));
    return;
  }
  const check = buildCheck("secrets", false, REASON_SECRETS_BLOCKED);
  recordCheck(check);
  const toolName = capabilityContext.toolName;
  const action = "cannot access secrets";
  const listText = JSON.stringify([...allowed].sort());
  const why = `Effective guarantees only allow secrets ${listText} (requested: ${secretName}).`;
  const example = `[capability_overrides]\n"${toolName}" = { secrets_allowed = ["${secretName}"] }`;
  throw new CapabilityViolation(buildBlockMessage(toolName, action, why, example), check);
}

function guardSubprocess(argv) {
  if (!capabilityContext) {
    return;
  }
  if (!capabilityContext.guarantees.no_subprocess) {
    recordCheck(buildCheck("subprocess", true, REASON_GUARANTEE_ALLOWED));
    return;
  }
  const check = buildCheck("subprocess", false, REASON_GUARANTEE_BLOCKED);
  recordCheck(check);
  const toolName = capabilityContext.toolName;
  const action = "cannot run subprocesses";
  const why = `Effective guarantees forbid subprocess access (${argv.join(" ")}).`;
  const example = `[capability_overrides]\n"${toolName}" = { no_subprocess = true }`;
  throw new CapabilityViolation(buildBlockMessage(toolName, action, why, example), check);
}


function isWriteMode(mode) {
  return /[wax+]/.test(String(mode || ""));
}

module.exports = {
  configureCapabilities,
  getCapabilityChecks,
};
