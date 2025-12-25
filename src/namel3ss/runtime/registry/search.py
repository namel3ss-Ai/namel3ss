from __future__ import annotations

from dataclasses import dataclass

from namel3ss.runtime.packs.policy import PackTrustPolicy, evaluate_policy
from namel3ss.runtime.packs.risk import risk_from_summary, risk_rank


@dataclass(frozen=True)
class DiscoverMatch:
    entry: dict[str, object]
    match_score: int
    matched_tokens: list[str]
    risk: str
    trusted: bool
    blocked: bool
    blocked_reasons: list[str]


def discover_entries(
    entries: list[dict[str, object]],
    *,
    phrase: str,
    policy: PackTrustPolicy,
    capability_filter: str | None = None,
    risk_filter: str | None = None,
) -> list[DiscoverMatch]:
    query_tokens = _tokenize(phrase)
    results: list[DiscoverMatch] = []
    for entry in entries:
        tokens = _entry_tokens(entry)
        overlap = sorted(set(query_tokens) & tokens)
        score = len(overlap)
        if query_tokens and score == 0:
            continue
        risk = _entry_risk(entry)
        if risk_filter and risk != risk_filter:
            continue
        if capability_filter and not _entry_has_capability(entry, capability_filter):
            continue
        trusted = bool(entry.get("verified_by"))
        decision = evaluate_policy(
            policy,
            operation="install",
            verified=trusted,
            risk=risk,
            capabilities=_capabilities_from_entry(entry),
        )
        results.append(
            DiscoverMatch(
                entry=entry,
                match_score=score,
                matched_tokens=overlap,
                risk=risk,
                trusted=trusted,
                blocked=not decision.allowed,
                blocked_reasons=decision.reasons,
            )
        )
    results.sort(key=lambda item: _sort_key(item))
    return results


def select_best_entry(
    entries: list[dict[str, object]],
    *,
    pack_id: str,
    pack_version: str,
    policy: PackTrustPolicy,
) -> DiscoverMatch | None:
    filtered = [entry for entry in entries if entry.get("pack_id") == pack_id and entry.get("pack_version") == pack_version]
    matches = discover_entries(filtered, phrase="", policy=policy)
    if not matches:
        return None
    allowed = [match for match in matches if not match.blocked]
    return allowed[0] if allowed else matches[0]


def _sort_key(match: DiscoverMatch) -> tuple[int, int, int, str]:
    trust_score = 1 if match.trusted else 0
    pack_name = str(match.entry.get("pack_name") or "")
    return (-trust_score, risk_rank(match.risk), -match.match_score, pack_name)


def _entry_tokens(entry: dict[str, object]) -> set[str]:
    tokens: list[str] = []
    tags = entry.get("intent_tags")
    if isinstance(tags, list):
        tokens.extend(str(item) for item in tags if isinstance(item, str))
    tools = entry.get("tools")
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, str):
                tokens.extend(_tokenize(tool))
    pack_name = entry.get("pack_name")
    if isinstance(pack_name, str):
        tokens.extend(_tokenize(pack_name))
    return set(tokens)


def _entry_risk(entry: dict[str, object]) -> str:
    capabilities = _capabilities_from_entry(entry)
    summary = {
        "levels": {
            "filesystem": capabilities.get("filesystem", "none"),
            "network": capabilities.get("network", "none"),
            "env": capabilities.get("env", "none"),
            "subprocess": capabilities.get("subprocess", "none"),
        },
        "secrets": capabilities.get("secrets", []),
    }
    runner_default = None
    runner = entry.get("runner")
    if isinstance(runner, dict):
        value = runner.get("default")
        if isinstance(value, str):
            runner_default = value
    return risk_from_summary(summary, runner_default)


def _capabilities_from_entry(entry: dict[str, object]) -> dict[str, object]:
    capabilities = entry.get("capabilities")
    if isinstance(capabilities, dict):
        return capabilities
    return {}


def _entry_has_capability(entry: dict[str, object], capability: str) -> bool:
    capabilities = _capabilities_from_entry(entry)
    if capability == "secrets":
        secrets = capabilities.get("secrets")
        return isinstance(secrets, list) and len(secrets) > 0
    if capability in {"filesystem", "network", "env", "subprocess"}:
        value = capabilities.get(capability)
        return isinstance(value, str) and value != "none"
    return False


def _tokenize(text: str) -> list[str]:
    stopwords = {"the", "and", "or", "to", "a", "an", "of", "for", "with", "this", "that", "is", "are", "be"}
    cleaned = []
    for ch in text.lower():
        cleaned.append(ch if ch.isalnum() else " ")
    tokens = [token for token in "".join(cleaned).split() if token and token not in stopwords]
    return tokens


__all__ = ["DiscoverMatch", "discover_entries", "select_best_entry"]
