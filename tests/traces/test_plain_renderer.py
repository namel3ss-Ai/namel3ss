from namel3ss.traces.plain import format_plain


def test_plain_renderer_flattens_memory_event():
    payload = {
        "type": "memory_recall",
        "policy": {"short_term": 2, "profile": False},
        "recalled": [{"id": "mem-1", "kind": "short_term"}],
    }
    expected = "\n".join(
        [
            "policy.profile: false",
            "policy.short_term: 2",
            "recalled.count: 1",
            "recalled.1.id: mem-1",
            "recalled.1.kind: short_term",
            "type: memory_recall",
        ]
    )
    assert format_plain(payload) == expected


def test_plain_renderer_escapes_newlines():
    payload = {"query": "hello\nworld"}
    assert format_plain(payload) == "query: hello\\nworld"


def test_plain_renderer_has_no_brackets():
    payload = {"type": "memory_write", "written": [{"id": "mem-1", "kind": "short_term"}]}
    rendered = format_plain(payload)
    assert all(ch not in rendered for ch in "{}[]()")
