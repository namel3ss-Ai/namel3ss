from namel3ss.runtime.memory_cache import (
    MemoryCacheStore,
    build_cache_event,
    build_cache_key,
    fingerprint_policy,
    fingerprint_query,
    use_cache,
)


def test_cache_key_is_stable():
    policy_a = {"alpha": 1, "beta": {"gamma": 2}}
    policy_b = {"beta": {"gamma": 2}, "alpha": 1}
    query_fingerprint = fingerprint_query("Hello world")
    policy_fingerprint = fingerprint_policy(policy_a)
    assert policy_fingerprint == fingerprint_policy(policy_b)
    key_one = build_cache_key(
        space="session",
        lane="my",
        phase_id="phase-1",
        ai_profile="assistant",
        store_key="session:owner:my",
        query_fingerprint=query_fingerprint,
        policy_fingerprint=policy_fingerprint,
    )
    key_two = build_cache_key(
        space="session",
        lane="my",
        phase_id="phase-1",
        ai_profile="assistant",
        store_key="session:owner:my",
        query_fingerprint=query_fingerprint,
        policy_fingerprint=policy_fingerprint,
    )
    assert key_one == key_two


def test_cache_eviction_is_deterministic():
    cache = MemoryCacheStore(max_entries=2)
    cache.set("one", "first", version=0)
    cache.set("two", "second", version=0)
    cache.set("three", "third", version=0)
    assert cache.get("one", version=0) is None
    assert cache.get("two", version=0) == "second"
    assert cache.get("three", version=0) == "third"


def test_cache_hit_and_miss():
    cache = MemoryCacheStore(max_entries=5)
    value, hit = use_cache(
        cache=cache,
        cache_enabled=True,
        cache_key="key",
        cache_version=0,
        compute=lambda: "value",
    )
    assert value == "value"
    assert hit is False
    value_two, hit_two = use_cache(
        cache=cache,
        cache_enabled=True,
        cache_key="key",
        cache_version=0,
        compute=lambda: "next",
    )
    assert value_two == "value"
    assert hit_two is True


def test_cache_trace_lines_have_no_brackets():
    hit_event = build_cache_event(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        lane="my",
        phase_id="phase-1",
        hit=True,
    )
    miss_event = build_cache_event(
        ai_profile="assistant",
        session="sess-1",
        space="session",
        lane="my",
        phase_id="phase-1",
        hit=False,
    )
    assert _no_brackets(hit_event.get("lines") or [])
    assert _no_brackets(miss_event.get("lines") or [])


def _no_brackets(lines: list[str]) -> bool:
    for line in lines:
        for ch in "[](){}":
            if ch in line:
                return False
    return True
