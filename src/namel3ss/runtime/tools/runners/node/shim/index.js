"use strict";

const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

function parseEntry(entry) {
  if (typeof entry !== "string") {
    throw new Error("Missing entry");
  }
  const idx = entry.indexOf(":");
  if (idx === -1) {
    throw new Error("Invalid entry");
  }
  const moduleSpec = entry.slice(0, idx).trim();
  const functionName = entry.slice(idx + 1).trim();
  if (!moduleSpec || !functionName) {
    throw new Error("Invalid entry");
  }
  return { moduleSpec, functionName };
}

function normalizeModuleSpec(spec) {
  return spec.replace(/\\/g, "/");
}

function moduleRoots(modulePaths) {
  if (Array.isArray(modulePaths) && modulePaths.length > 0) {
    return modulePaths;
  }
  return [process.cwd()];
}

function toToolsPath(spec) {
  if (spec === "tools") {
    return "tools";
  }
  if (spec.startsWith("tools/")) {
    return spec;
  }
  if (spec.startsWith("tools.")) {
    const suffix = spec.slice("tools.".length);
    return path.join("tools", ...suffix.split("."));
  }
  return null;
}

function resolveFileCandidate(basePath) {
  const ext = path.extname(basePath);
  const exts = ["", ".js", ".cjs", ".mjs", ".ts"];
  const candidates = [];
  if (ext) {
    candidates.push(basePath);
  } else {
    for (const suffix of exts) {
      candidates.push(basePath + suffix);
    }
    for (const suffix of exts) {
      candidates.push(path.join(basePath, "index" + suffix));
    }
  }
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return null;
}

function resolveModuleTarget(moduleSpec, modulePaths) {
  const normalized = normalizeModuleSpec(moduleSpec);
  const toolsPath = toToolsPath(normalized);
  const roots = moduleRoots(modulePaths);
  if (toolsPath) {
    for (const root of roots) {
      const candidate = resolveFileCandidate(path.resolve(root, toolsPath));
      if (candidate) {
        return { target: candidate, isPath: true };
      }
    }
  }
  if (normalized.startsWith("./") || normalized.startsWith("../") || normalized.startsWith("/")) {
    for (const root of roots) {
      const candidate = resolveFileCandidate(path.resolve(root, normalized));
      if (candidate) {
        return { target: candidate, isPath: true };
      }
    }
  }
  return { target: moduleSpec, isPath: false };
}

function ensureTypeScriptSupport() {
  try {
    require("ts-node/register/transpile-only");
    return true;
  } catch (err) {
    try {
      require("ts-node/register");
      return true;
    } catch (err2) {
      return false;
    }
  }
}

async function loadModule(target, isPath) {
  if (isPath && target.endsWith(".ts")) {
    if (!ensureTypeScriptSupport()) {
      const error = new Error("TypeScript support requires ts-node");
      error.name = "TypeScriptError";
      throw error;
    }
  }
  try {
    return require(target);
  } catch (err) {
    if (err && err.code === "ERR_REQUIRE_ESM") {
      const spec = isPath ? pathToFileURL(target).href : target;
      return import(spec);
    }
    throw err;
  }
}

function pickFunction(moduleValue, functionName) {
  if (moduleValue && typeof moduleValue === "object" && functionName in moduleValue) {
    return moduleValue[functionName];
  }
  if (typeof moduleValue === "function" && (functionName === "default" || functionName === "run")) {
    return moduleValue;
  }
  if (moduleValue && moduleValue.default) {
    const def = moduleValue.default;
    if (typeof def === "function" && functionName === "default") {
      return def;
    }
    if (def && typeof def === "object" && functionName in def) {
      return def[functionName];
    }
  }
  return null;
}

function captureOutput() {
  const originalStdoutWrite = process.stdout.write.bind(process.stdout);
  const originalStderrWrite = process.stderr.write.bind(process.stderr);
  process.stdout.write = (chunk, encoding, cb) => {
    if (typeof cb === "function") {
      cb();
    }
    return true;
  };
  process.stderr.write = (chunk, encoding, cb) => {
    if (typeof cb === "function") {
      cb();
    }
    return true;
  };
  return () => {
    process.stdout.write = originalStdoutWrite;
    process.stderr.write = originalStderrWrite;
  };
}

const { configureCapabilities, getCapabilityChecks } = require("./capabilities");

async function runTool(payload) {
  const { moduleSpec, functionName } = parseEntry(payload.entry);
  const resolved = resolveModuleTarget(moduleSpec, payload.module_paths);
  const mod = await loadModule(resolved.target, resolved.isPath);
  const fn = pickFunction(mod, functionName);
  if (typeof fn !== "function") {
    throw new Error("Entry target is not callable");
  }
  return await Promise.resolve(fn(payload.payload));
}

function errorType(err) {
  if (err && err.name) {
    return String(err.name);
  }
  return "Error";
}

function errorMessage(err) {
  if (err && err.message) {
    return String(err.message);
  }
  return String(err);
}

function errorPayload(err) {
  const error = { type: errorType(err), message: errorMessage(err) };
  if (err && err.check && err.check.reason) {
    error.reason_code = String(err.check.reason);
  }
  return error;
}

async function runPayload(payload) {
  const restore = captureOutput();
  configureCapabilities(payload);
  try {
    const result = await runTool(payload);
    return {
      ok: true,
      result,
      protocol_version: payload.protocol_version || 1,
      capability_checks: getCapabilityChecks(),
    };
  } catch (err) {
    return {
      ok: false,
      error: errorPayload(err),
      protocol_version: payload.protocol_version || 1,
      capability_checks: getCapabilityChecks(),
    };
  } finally {
    restore();
  }
}

async function main() {
  let payload;
  try {
    const text = await readStdin();
    payload = JSON.parse(text || "{}");
  } catch (err) {
    const out = {
      ok: false,
      error: { type: errorType(err), message: errorMessage(err) },
      protocol_version: 1,
    };
    process.stdout.write(JSON.stringify(out));
    return 1;
  }
  const response = await runPayload(payload);
  try {
    process.stdout.write(JSON.stringify(response));
    return 0;
  } catch (err) {
    const out = {
      ok: false,
      error: { type: errorType(err), message: errorMessage(err) },
      protocol_version: payload.protocol_version || 1,
    };
    process.stdout.write(JSON.stringify(out));
    return 1;
  }
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    const out = {
      ok: false,
      error: { type: errorType(err), message: errorMessage(err) },
      protocol_version: 1,
    };
    process.stdout.write(JSON.stringify(out));
    process.exit(1);
  });
