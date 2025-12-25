from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.guidance import build_guidance_message
from namel3ss.runtime.capabilities.effective import summarize_guarantees
from namel3ss.runtime.packs.capabilities import capabilities_summary, parse_capabilities_yaml
from namel3ss.runtime.packs.intent import summarize_intent
from namel3ss.runtime.packs.manifest import PackManifest, parse_pack_manifest_text
from namel3ss.runtime.packs.runners import pack_runner_default
from namel3ss.runtime.packs.trust_store import load_trusted_keys
from namel3ss.runtime.packs.verification import compute_pack_digest
from namel3ss.runtime.tools.bindings_yaml import ToolBinding, parse_bindings_yaml
from namel3ss.runtime.registry.entry import RegistryEntry, normalize_registry_entry


@dataclass(frozen=True)
class BundleEntryResult:
    entry: RegistryEntry
    manifest: PackManifest
    tools_text: str | None
    manifest_text: str


def build_registry_entry_from_bundle(
    bundle_path: Path,
    *,
    app_root: Path,
    source_kind: str,
    source_uri: str,
) -> BundleEntryResult:
    if not bundle_path.exists():
        raise Namel3ssError(_missing_bundle_message(bundle_path))
    manifest_text, tools_text, intent_text, caps_text, signature_text = _read_bundle_texts(bundle_path)
    manifest = parse_pack_manifest_text(manifest_text, bundle_path / "pack.yaml")
    bindings = _parse_bindings(bundle_path, tools_text, manifest.entrypoints)
    summary, guarantees = _capabilities_summary(bundle_path, caps_text)
    runner_default = pack_runner_default(manifest, bindings)
    digest = _bundle_digest(bundle_path)
    signed, verified_by = _signature_status(app_root, manifest_text, tools_text, signature_text)
    intent_phrases = _intent_phrases(intent_text, manifest, bindings)
    intent_tags = _intent_tags(intent_phrases, manifest.tools)
    entry = RegistryEntry(
        entry_version=1,
        pack_id=manifest.pack_id,
        pack_name=manifest.name,
        pack_version=manifest.version,
        pack_digest=digest,
        signer_id=manifest.signer_id,
        verified_by=verified_by,
        tools=manifest.tools,
        intent_tags=intent_tags,
        intent_phrases=intent_phrases,
        capabilities=_flatten_capabilities(summary),
        guarantees=guarantees,
        runner={
            "default": runner_default,
            "service_url": manifest.service_url,
            "container_image": manifest.container_image,
        },
        source={"kind": source_kind, "uri": source_uri},
    )
    entry_dict = normalize_registry_entry(entry.to_dict())
    entry = RegistryEntry(**entry_dict)
    return BundleEntryResult(entry=entry, manifest=manifest, tools_text=tools_text, manifest_text=manifest_text)


def _bundle_digest(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _read_bundle_texts(
    bundle_path: Path,
) -> tuple[str, str | None, str, str | None, str | None]:
    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = archive.namelist()
        manifest_name = _find_name(names, "pack.yaml")
        if not manifest_name:
            raise Namel3ssError(_missing_manifest_message(bundle_path))
        manifest_text = archive.read(manifest_name).decode("utf-8")
        tools_text = _read_optional_text(archive, names, "tools.yaml")
        intent_text = _read_optional_text(archive, names, "intent.md") or ""
        caps_text = _read_optional_text(archive, names, "capabilities.yaml")
        signature_text = _read_optional_text(archive, names, "signature.txt")
    if not intent_text:
        raise Namel3ssError(_missing_intent_message(bundle_path))
    return manifest_text, tools_text, intent_text, caps_text, signature_text


def _read_optional_text(archive: zipfile.ZipFile, names: list[str], filename: str) -> str | None:
    match = _find_name(names, filename)
    if not match:
        return None
    return archive.read(match).decode("utf-8")


def _find_name(names: list[str], filename: str) -> str | None:
    matches = [name for name in names if name == filename or name.endswith(f"/{filename}")]
    if not matches:
        return None
    return min(matches, key=len)


def _parse_bindings(
    bundle_path: Path,
    tools_text: str | None,
    entrypoints: dict[str, ToolBinding] | None,
) -> dict[str, ToolBinding]:
    if tools_text is None:
        return dict(entrypoints or {})
    return parse_bindings_yaml(tools_text, bundle_path / "tools.yaml")


def _capabilities_summary(
    bundle_path: Path,
    caps_text: str | None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    if caps_text is None:
        return (
            {"levels": {"filesystem": "none", "network": "none", "env": "none", "subprocess": "none"}, "secrets": []},
            None,
        )
    caps = parse_capabilities_yaml(caps_text, bundle_path / "capabilities.yaml")
    return capabilities_summary(caps), summarize_guarantees(caps)


def _signature_status(
    app_root: Path,
    manifest_text: str,
    tools_text: str | None,
    signature_text: str | None,
) -> tuple[bool, list[str]]:
    if not signature_text:
        return False, []
    signature = signature_text.strip()
    if not signature:
        return False, []
    if not signature.startswith("sha256:"):
        signature = f"sha256:{signature}"
    digest = compute_pack_digest(manifest_text, tools_text)
    if signature != digest:
        return False, []
    keys = load_trusted_keys(app_root)
    verified_by = [key.key_id for key in keys if key.public_key == signature or key.public_key == digest]
    return True, sorted(verified_by)


def _intent_phrases(intent_text: str, manifest: PackManifest, bindings: dict[str, ToolBinding]) -> list[str]:
    summary = summarize_intent(intent_text)
    if summary.missing:
        raise Namel3ssError(_missing_intent_headings_message(summary.missing))
    phrases: list[str] = []
    what_body = _section_body(intent_text, "What this pack does")
    if what_body:
        line = _first_non_empty_line(what_body)
        if line:
            phrases.append(line)
    tools_body = _section_body(intent_text, "Tools provided (English)")
    if tools_body:
        for line in tools_body.splitlines():
            stripped = line.strip().lstrip("-").strip()
            stripped = _strip_quotes(stripped)
            if stripped:
                phrases.append(stripped)
    if not phrases:
        phrases.append(manifest.name)
    if bindings:
        for tool_name in bindings:
            phrases.append(tool_name)
    return _dedupe_preserve_order(phrases)


def _intent_tags(phrases: list[str], tools: list[str]) -> list[str]:
    tokens: list[str] = []
    for text in phrases + tools:
        tokens.extend(_tokenize(text))
    return sorted(dict.fromkeys(tokens))


def _tokenize(text: str) -> list[str]:
    stopwords = {"the", "and", "or", "to", "a", "an", "of", "for", "with", "this", "that", "is", "are", "be"}
    cleaned = []
    for ch in text.lower():
        cleaned.append(ch if ch.isalnum() else " ")
    tokens = [token for token in "".join(cleaned).split() if token and token not in stopwords]
    return tokens


def _flatten_capabilities(summary: dict[str, object]) -> dict[str, object]:
    levels = summary.get("levels") if isinstance(summary, dict) else {}
    if not isinstance(levels, dict):
        levels = {}
    return {
        "filesystem": str(levels.get("filesystem", "none")),
        "network": str(levels.get("network", "none")),
        "env": str(levels.get("env", "none")),
        "subprocess": str(levels.get("subprocess", "none")),
        "secrets": list(summary.get("secrets", [])) if isinstance(summary, dict) else [],
    }


def _section_body(text: str, heading: str) -> str | None:
    normalized = _normalize_heading(heading)
    lines = text.splitlines()
    start = None
    for idx, raw in enumerate(lines):
        line = raw.strip()
        if not line.startswith("#"):
            continue
        found = _normalize_heading(line.lstrip("#").strip())
        if found == normalized:
            start = idx + 1
            break
    if start is None:
        return None
    body_lines: list[str] = []
    for raw in lines[start:]:
        if raw.strip().startswith("#"):
            break
        body_lines.append(raw)
    return "\n".join(body_lines)


def _normalize_heading(text: str) -> str:
    return " ".join(text.lower().split())


def _first_non_empty_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _missing_bundle_message(path: Path) -> str:
    return build_guidance_message(
        what="Bundle path was not found.",
        why=f"Expected {path.as_posix()} to exist.",
        fix="Pass a valid .n3pack.zip file.",
        example="n3 registry add ./dist/pack.n3pack.zip",
    )


def _missing_manifest_message(path: Path) -> str:
    return build_guidance_message(
        what="Bundle is missing pack.yaml.",
        why=f"{path.as_posix()} does not contain pack.yaml.",
        fix="Bundle the pack again.",
        example="n3 packs bundle ./pack --out ./dist",
    )


def _missing_intent_message(path: Path) -> str:
    return build_guidance_message(
        what="Bundle is missing intent.md.",
        why=f"{path.as_posix()} does not contain intent.md.",
        fix="Add intent.md and rebuild the bundle.",
        example="intent.md",
    )


def _missing_intent_headings_message(missing: list[str]) -> str:
    return build_guidance_message(
        what="Bundle intent.md is missing required headings.",
        why=f"Missing headings: {', '.join(missing)}.",
        fix="Add the missing headings and rebuild the bundle.",
        example="intent.md",
    )


__all__ = ["BundleEntryResult", "build_registry_entry_from_bundle"]
