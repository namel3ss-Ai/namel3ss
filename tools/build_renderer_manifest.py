from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from namel3ss.determinism import canonical_json_dumps
from namel3ss.studio.renderer_registry.manifest_schema import RENDERER_MANIFEST_SCHEMA_VERSION


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "src" / "namel3ss" / "studio" / "web"
MANIFEST_PATH = WEB_ROOT / "renderer_manifest.json"
REGISTRY_PATH = WEB_ROOT / "renderer_registry.js"

ENTRYPOINT_PREFIX = "ui_renderer_"
ENTRYPOINT_SUFFIX = ".js"
REQUIRED_RENDERERS: tuple[str, ...] = ("audit_viewer", "state_inspector")
RENDERER_ID_ALIASES = {"state_viewer": "state_inspector"}
RENDERER_EXPORT_PATTERN = re.compile(r"(?:root|window(?:\.N3UIRender)?)\.([A-Za-z_][A-Za-z0-9_]*)\s*=")
WINDOW_EXPORT_PATTERN = re.compile(r"window\.([A-Za-z_][A-Za-z0-9_]*)\s*=")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Studio renderer manifest and loader registry.")
    parser.add_argument("--check", action="store_true", help="Verify files are up to date without writing.")
    args = parser.parse_args(argv)

    manifest = build_manifest()
    manifest_text = canonical_json_dumps(manifest, pretty=True, drop_run_keys=False)
    registry_text = build_registry_loader(manifest)

    if args.check:
        return check_outputs(manifest_text, registry_text)
    write_outputs(manifest_text, registry_text)
    return 0


def build_manifest() -> dict[str, object]:
    entries: list[dict[str, object]] = []
    for path in sorted(WEB_ROOT.glob(f"{ENTRYPOINT_PREFIX}*{ENTRYPOINT_SUFFIX}"), key=lambda item: item.name):
        renderer_key = path.name[len(ENTRYPOINT_PREFIX) : -len(ENTRYPOINT_SUFFIX)]
        renderer_id = RENDERER_ID_ALIASES.get(renderer_key, renderer_key)
        text = path.read_text(encoding="utf-8")
        exports = sorted(set(find_exports(text)))
        entrypoint = path.name
        entries.append(
            {
                "entrypoint": entrypoint,
                "entrypoint_hash": f"sha256:{sha256_text(entrypoint)}",
                "exports": exports,
                "integrity_hash": f"sha256:{sha256_text(text)}",
                "renderer_id": renderer_id,
                "version": "1",
            }
        )
    entries.sort(key=lambda item: str(item["renderer_id"]))
    return {"renderers": entries, "schema_version": RENDERER_MANIFEST_SCHEMA_VERSION}


def find_exports(source: str) -> list[str]:
    exports: list[str] = []
    for pattern in (RENDERER_EXPORT_PATTERN, WINDOW_EXPORT_PATTERN):
        for match in pattern.finditer(source):
            value = match.group(1).strip()
            if value and value.startswith("render"):
                exports.append(value)
    return exports


def build_registry_loader(manifest: dict[str, object]) -> str:
    manifest_js = canonical_json_dumps(manifest, pretty=True, drop_run_keys=False).strip()
    required_js = ", ".join([f'"{item}"' for item in REQUIRED_RENDERERS])
    return (
        "(() => {\n"
        f"  const MANIFEST = {manifest_js};\n"
        f"  const REQUIRED_RENDERERS = [{required_js}];\n"
        '  const ERROR_REQUIRED_MISSING = "N3E_RENDERER_REQUIRED_MISSING";\n'
        '  const ERROR_REGISTRY_INVALID = "N3E_RENDERER_REGISTRY_INVALID";\n'
        "  const loadedEntrypoints = new Set();\n"
        "  const root = window.N3UIRender || (window.N3UIRender = {});\n\n"
        "  function fail(errorCode, message) {\n"
        "    const error = new Error(message);\n"
        "    error.error_code = errorCode;\n"
        "    throw error;\n"
        "  }\n\n"
        "  function asText(value) {\n"
        '    return typeof value === "string" ? value.trim() : "";\n'
        "  }\n\n"
        "  function validateManifestShape() {\n"
        "    if (!MANIFEST || typeof MANIFEST !== \"object\") {\n"
        "      fail(ERROR_REGISTRY_INVALID, \"renderer manifest must be an object.\");\n"
        "    }\n"
        "    const renderers = Array.isArray(MANIFEST.renderers) ? MANIFEST.renderers : null;\n"
        "    if (!renderers) {\n"
        "      fail(ERROR_REGISTRY_INVALID, \"renderer manifest.renderers must be a list.\");\n"
        "    }\n"
        "    const ids = [];\n"
        "    const seen = new Set();\n"
        "    for (const entry of renderers) {\n"
        "      if (!entry || typeof entry !== \"object\") {\n"
        "        fail(ERROR_REGISTRY_INVALID, \"renderer entries must be objects.\");\n"
        "      }\n"
        "      const rendererId = asText(entry.renderer_id);\n"
        "      const entrypoint = asText(entry.entrypoint);\n"
        "      if (!rendererId || !entrypoint) {\n"
        "        fail(ERROR_REGISTRY_INVALID, \"renderer entry requires renderer_id and entrypoint.\");\n"
        "      }\n"
        "      if (seen.has(rendererId)) {\n"
        "        fail(ERROR_REGISTRY_INVALID, `duplicate renderer_id: ${rendererId}`);\n"
        "      }\n"
        "      seen.add(rendererId);\n"
        "      ids.push(rendererId);\n"
        "    }\n"
        "    const sorted = ids.slice().sort();\n"
        "    if (JSON.stringify(ids) !== JSON.stringify(sorted)) {\n"
        "      fail(ERROR_REGISTRY_INVALID, \"renderer entries must be sorted by renderer_id.\");\n"
        "    }\n"
        "    const missing = REQUIRED_RENDERERS.filter((item) => !seen.has(item));\n"
        "    if (missing.length) {\n"
        "      fail(ERROR_REQUIRED_MISSING, `required renderer(s) missing: ${missing.join(\", \")}`);\n"
        "    }\n"
        "    return renderers;\n"
        "  }\n\n"
        "  function loadRendererScript(entrypoint) {\n"
        "    if (loadedEntrypoints.has(entrypoint)) return Promise.resolve();\n"
        "    loadedEntrypoints.add(entrypoint);\n"
        "    return new Promise((resolve, reject) => {\n"
        "      const script = document.createElement(\"script\");\n"
        "      script.src = `/${entrypoint}`;\n"
        "      script.async = false;\n"
        "      script.defer = false;\n"
        "      script.dataset.n3RendererEntrypoint = entrypoint;\n"
        "      script.onload = () => resolve();\n"
        "      script.onerror = () => reject(new Error(`failed to load renderer script: ${entrypoint}`));\n"
        "      document.head.appendChild(script);\n"
        "    });\n"
        "  }\n\n"
        "  function assertExports(entry) {\n"
        "    const rendererId = asText(entry.renderer_id);\n"
        "    const exports = Array.isArray(entry.exports) ? entry.exports : [];\n"
        "    for (const exportName of exports) {\n"
        "      const key = asText(exportName);\n"
        "      if (!key) continue;\n"
        "      const value = root[key] || window[key];\n"
        "      if (typeof value !== \"function\") {\n"
        "        fail(ERROR_REGISTRY_INVALID, `renderer '${rendererId}' missing export '${key}'.`);\n"
        "      }\n"
        "    }\n"
        "  }\n\n"
        "  async function bootstrap() {\n"
        "    const renderers = validateManifestShape();\n"
        "    for (const entry of renderers) {\n"
        "      await loadRendererScript(asText(entry.entrypoint));\n"
        "      assertExports(entry);\n"
        "    }\n"
        "  }\n\n"
        "  const ready = bootstrap();\n"
        "  window.N3RendererRegistry = {\n"
        "    manifest: MANIFEST,\n"
        "    ready,\n"
        "    rendererIds: Array.isArray(MANIFEST.renderers)\n"
        "      ? MANIFEST.renderers.map((entry) => asText(entry.renderer_id)).filter(Boolean)\n"
        "      : [],\n"
        "  };\n"
        "})();\n"
    )


def check_outputs(manifest_text: str, registry_text: str) -> int:
    manifest_current = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
    registry_current = REGISTRY_PATH.read_text(encoding="utf-8") if REGISTRY_PATH.exists() else ""
    if manifest_current != manifest_text or registry_current != registry_text:
        print("Renderer registry assets are out of date. Run: python tools/build_renderer_manifest.py")
        return 1
    return 0


def write_outputs(manifest_text: str, registry_text: str) -> None:
    MANIFEST_PATH.write_text(manifest_text, encoding="utf-8", newline="\n")
    REGISTRY_PATH.write_text(registry_text, encoding="utf-8", newline="\n")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
