from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.utils.slugify import slugify_text


_LANG_ALIASES = {
    "node": "node",
    "js": "node",
    "javascript": "node",
    "go": "go",
    "golang": "go",
    "rust": "rust",
}


@dataclass(frozen=True)
class PluginTemplate:
    language: str
    command: str
    files: dict[str, str]


def scaffold_plugin(language: str, name: str, root: Path) -> Path:
    language_key = _resolve_language(language)
    slug = _slugify_name(name)
    template = _render_template(language_key, slug, display=name.strip() or slug)
    target = root / slug
    if target.exists():
        raise Namel3ssError(_existing_dir_message(target))
    target.mkdir(parents=True, exist_ok=False)
    for rel_path in sorted(template.files.keys()):
        dest = target / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(template.files[rel_path], encoding="utf-8")
    return target


def render_plugin_files(language: str, name: str) -> dict[str, str]:
    language_key = _resolve_language(language)
    slug = _slugify_name(name)
    template = _render_template(language_key, slug, display=name.strip() or slug)
    return dict(template.files)


def _render_template(language: str, slug: str, *, display: str) -> PluginTemplate:
    if language == "node":
        command = "node index.js"
        files = {
            "README.md": _render_readme(display, command, slug),
            "package.json": _render_node_package(slug),
            "index.js": _render_node_plugin(),
        }
        return PluginTemplate(language="node", command=command, files=files)
    if language == "go":
        command = "go run ."
        files = {
            "README.md": _render_readme(display, command, slug),
            "go.mod": _render_go_mod(slug),
            "main.go": _render_go_plugin(),
        }
        return PluginTemplate(language="go", command=command, files=files)
    if language == "rust":
        command = "cargo run --quiet"
        files = {
            "README.md": _render_readme(display, command, slug),
            "Cargo.toml": _render_rust_toml(slug),
            "src/main.rs": _render_rust_plugin(),
        }
        return PluginTemplate(language="rust", command=command, files=files)
    raise Namel3ssError(_unknown_language_message(language))


def _render_readme(name: str, command: str, flow_name: str) -> str:
    lines = [
        f"# {name} plugin",
        "",
        "This plugin follows the namel3ss plugin protocol.",
        "",
        "Input payload fields:",
        "- inputs (map)",
        "- state (map)",
        "- identity (map, optional)",
        "",
        "Output payload fields:",
        "- ok (true or false)",
        "- result (map when ok is true)",
        "- error (map with type and message when ok is false)",
        "",
        "Run locally:",
        f"- {command}",
        "",
        "Sandbox config example:",
        "sandboxes:",
        f"  {flow_name}:",
        f"    command: \"{command}\"",
        "",
    ]
    return "\n".join(lines)


def _render_node_package(slug: str) -> str:
    lines = [
        "{",
        f'  "name": "{slug}",',
        '  "version": "0.1.0",',
        '  "main": "index.js"',
        "}",
        "",
    ]
    return "\n".join(lines)


def _render_node_plugin() -> str:
    lines = [
        'const fs = require("fs");',
        "",
        "function readPayload() {",
        "  try {",
        '    const text = fs.readFileSync(0, "utf8");',
        "    if (!text.trim()) {",
        "      return {};",
        "    }",
        "    return JSON.parse(text);",
        "  } catch (err) {",
        "    return { __parse_error: String(err) };",
        "  }",
        "}",
        "",
        "const payload = readPayload();",
        "if (payload.__parse_error) {",
        "  const response = {",
        "    ok: false,",
        "    error: { type: \"ParseError\", message: \"Input was not valid JSON.\" },",
        "  };",
        "  process.stdout.write(JSON.stringify(response));",
        "  process.exit(0);",
        "}",
        "",
        "const inputs = payload.inputs || payload.input || {};",
        "const state = payload.state || {};",
        "const outputs = { inputs, state };",
        "const response = { ok: true, result: outputs };",
        "process.stdout.write(JSON.stringify(response));",
        "",
    ]
    return "\n".join(lines)


def _render_go_mod(slug: str) -> str:
    return f"module {slug}\n\ngo 1.20\n"


def _render_go_plugin() -> str:
    lines = [
        "package main",
        "",
        "import (",
        "  \"encoding/json\"",
        "  \"io\"",
        "  \"os\"",
        ")",
        "",
        "func main() {",
        "  raw, _ := io.ReadAll(os.Stdin)",
        "  payload := map[string]any{}",
        "  if len(raw) > 0 {",
        "    if err := json.Unmarshal(raw, &payload); err != nil {",
        "      writeError(\"ParseError\", \"Input was not valid JSON.\")",
        "      return",
        "    }",
        "  }",
        "  inputs, ok := payload[\"inputs\"].(map[string]any)",
        "  if !ok || inputs == nil {",
        "    if legacy, ok := payload[\"input\"].(map[string]any); ok {",
        "      inputs = legacy",
        "    } else {",
        "      inputs = map[string]any{}",
        "    }",
        "  }",
        "  state, ok := payload[\"state\"].(map[string]any)",
        "  if !ok || state == nil {",
        "    state = map[string]any{}",
        "  }",
        "  outputs := map[string]any{\"inputs\": inputs, \"state\": state}",
        "  response := map[string]any{\"ok\": true, \"result\": outputs}",
        "  encoded, _ := json.Marshal(response)",
        "  os.Stdout.Write(encoded)",
        "}",
        "",
        "func writeError(kind string, message string) {",
        "  response := map[string]any{",
        "    \"ok\": false,",
        "    \"error\": map[string]any{",
        "      \"type\": kind,",
        "      \"message\": message,",
        "    },",
        "  }",
        "  encoded, _ := json.Marshal(response)",
        "  os.Stdout.Write(encoded)",
        "}",
        "",
    ]
    return "\n".join(lines)


def _render_rust_toml(slug: str) -> str:
    lines = [
        "[package]",
        f"name = \"{slug}\"",
        "version = \"0.1.0\"",
        "edition = \"2021\"",
        "",
        "[dependencies]",
        "serde_json = \"1.0\"",
        "",
    ]
    return "\n".join(lines)


def _render_rust_plugin() -> str:
    lines = [
        "use serde_json::json;",
        "use serde_json::Value;",
        "use std::io::Read;",
        "",
        "fn main() {",
        "    let mut input = String::new();",
        "    let _ = std::io::stdin().read_to_string(&mut input);",
        "    let payload: Value = if input.trim().is_empty() {",
        "        json!({})",
        "    } else {",
        "        serde_json::from_str(&input).unwrap_or(json!({\"__parse_error\": true}))",
        "    };",
        "    if payload.get(\"__parse_error\").is_some() {",
        "        let response = json!({",
        "            \"ok\": false,",
        "            \"error\": {",
        "                \"type\": \"ParseError\",",
        "                \"message\": \"Input was not valid JSON.\",",
        "            }",
        "        });",
        "        println!(\"{}\", response.to_string());",
        "        return;",
        "    }",
        "    let inputs = payload.get(\"inputs\").cloned().or_else(|| payload.get(\"input\").cloned()).unwrap_or(json!({}));",
        "    let state = payload.get(\"state\").cloned().unwrap_or(json!({}));",
        "    let response = json!({",
        "        \"ok\": true,",
        "        \"result\": {",
        "            \"inputs\": inputs,",
        "            \"state\": state,",
        "        }",
        "    });",
        "    println!(\"{}\", response.to_string());",
        "}",
        "",
    ]
    return "\n".join(lines)


def _resolve_language(value: str) -> str:
    key = (value or "").strip().lower()
    if not key:
        raise Namel3ssError(_unknown_language_message(value))
    if key not in _LANG_ALIASES:
        raise Namel3ssError(_unknown_language_message(value))
    return _LANG_ALIASES[key]


def _slugify_name(name: str) -> str:
    slug = slugify_text(name)
    if not slug:
        raise Namel3ssError("Plugin name is required.")
    return slug


def _existing_dir_message(target: Path) -> str:
    return build_guidance_message(
        what=f"Plugin directory already exists: {target}.",
        why="Scaffolding would overwrite existing files.",
        fix="Use a new name or remove the existing directory.",
        example="n3 plugin new node demo_plugin",
    )


def _unknown_language_message(language: str) -> str:
    available = ", ".join(sorted({value for value in _LANG_ALIASES.values()}))
    return build_guidance_message(
        what=f"Unknown plugin language '{language}'.",
        why=f"Supported languages are: {available}.",
        fix="Choose a supported language.",
        example="n3 plugin new node demo_plugin",
    )


__all__ = ["PluginTemplate", "render_plugin_files", "scaffold_plugin"]
