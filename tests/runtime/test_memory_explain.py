from namel3ss.runtime.memory_explain import (
    append_explanation_events,
    explain_memory_conflict,
    explain_memory_deleted,
    explain_memory_denied,
    explain_memory_forget,
    explain_memory_phase_diff,
    explain_memory_recall,
)


def test_explain_memory_recall():
    event = {
        "type": "memory_recall",
        "current_phase": {"phase_id": "phase-2"},
        "spaces_consulted": ["project", "session"],
        "recalled": [
            {"meta": {"recall_reason": ["recency", "space:session"]}},
            {"meta": {"recall_reason": ["matches_query", "importance"]}},
        ],
        "policy": {"phase_mode": "current_only"},
        "recall_counts": {"session": 2, "project": 0},
        "phase_counts": {"session": {"phase-2": 2}},
    }
    explanation = explain_memory_recall(event)
    assert explanation.title == "Memory recall"
    assert explanation.lines == [
        "Phase used is phase-2.",
        "Spaces checked are session, project.",
        "Recalled items count is 2.",
        "Only the current phase was used.",
        "Older phases were ignored.",
        "Items recalled from session count is 2.",
        "No items were recalled from project.",
        "Phase phase-2 count in session is 2.",
        "Recall reason is it matches your question.",
        "Recall reason is it is recent.",
        "Recall reason is it is marked important.",
    ]


def test_explain_memory_denied():
    event = {
        "type": "memory_denied",
        "attempted": {"kind": "semantic", "meta": {"event_type": "fact"}},
        "reason": "privacy_deny_sensitive",
    }
    explanation = explain_memory_denied(event)
    assert explanation.title == "Memory denied"
    assert explanation.lines == [
        "Write was blocked.",
        "Blocked kind is semantic.",
        "Blocked event type is fact.",
        "Policy blocks sensitive content.",
        "Remove secrets or tokens.",
    ]


def test_explain_memory_deleted():
    event = {
        "type": "memory_deleted",
        "memory_id": "session:1:short_term:2",
        "reason": "conflict_loser",
        "replaced_by": "session:1:short_term:3",
    }
    explanation = explain_memory_deleted(event)
    assert explanation.title == "Memory deleted"
    assert explanation.lines == [
        "Deleted id is session:1:short_term:2.",
        "Item lost a conflict.",
        "Replaced by id is session:1:short_term:3.",
    ]
    assert explanation.related_ids == ["session:1:short_term:2", "session:1:short_term:3"]


def test_explain_memory_forget():
    event = {"type": "memory_forget", "memory_id": "session:1:semantic:9", "reason": "decay"}
    explanation = explain_memory_forget(event)
    assert explanation.title == "Memory forgotten"
    assert explanation.lines == [
        "Forgotten id is session:1:semantic:9.",
        "Item decayed by age.",
    ]


def test_explain_memory_conflict():
    event = {"type": "memory_conflict", "winner_id": "id2", "loser_id": "id1", "rule": "authority"}
    explanation = explain_memory_conflict(event)
    assert explanation.title == "Memory conflict"
    assert explanation.lines == [
        "Conflict detected.",
        "Winner id is id2.",
        "Loser id is id1.",
        "Winner had higher authority.",
    ]
    assert explanation.related_ids == ["id2", "id1"]


def test_explain_memory_phase_diff():
    event = {
        "type": "memory_phase_diff",
        "from_phase_id": "phase-1",
        "to_phase_id": "phase-2",
        "added_count": 1,
        "deleted_count": 2,
        "replaced_count": 1,
        "top_changes": [
            {"change": "added", "memory_id": "a1", "kind": "semantic"},
            {"change": "deleted", "memory_id": "b1", "kind": "profile"},
            {"change": "replaced", "from_id": "c1", "to_id": "c2"},
        ],
    }
    explanation = explain_memory_phase_diff(event)
    assert explanation.title == "Memory phase diff"
    assert explanation.lines == [
        "Phase diff from phase-1 to phase-2.",
        "Added count is 1.",
        "Deleted count is 2.",
        "Replaced count is 1.",
        "Added a1 kind semantic.",
        "Deleted b1 kind profile.",
        "Replaced c1 with c2.",
    ]


def test_append_explanation_events_inserts_events():
    events = [
        {"type": "memory_recall", "current_phase": {"phase_id": "phase-1"}, "recalled": []},
        {"type": "ai_call_started", "trace_version": "2024-10-01"},
        {
            "type": "memory_denied",
            "attempted": {"kind": "semantic", "meta": {"event_type": "fact"}},
            "reason": "privacy_deny_sensitive",
        },
    ]
    explained = append_explanation_events(events)
    types = [event["type"] for event in explained]
    assert types == [
        "memory_recall",
        "memory_explanation",
        "ai_call_started",
        "memory_denied",
        "memory_explanation",
    ]
    assert explained[1]["for_event_index"] == 0
    assert explained[4]["for_event_index"] == 3
