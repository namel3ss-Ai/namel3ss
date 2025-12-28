from namel3ss.runtime.memory.contract import MemoryClock, MemoryIdGenerator, MemoryItemFactory, MemoryKind
from namel3ss.runtime.memory.manager import MemoryManager
from namel3ss.runtime.memory_links.apply import add_link_to_item, build_link_record
from namel3ss.runtime.memory_links.model import LINK_TYPE_PROMOTED_FROM, LINK_TYPE_REPLACED
from namel3ss.runtime.memory_links.preview import preview_text
from namel3ss.runtime.memory_links.render import link_lines, path_lines
from tests.conftest import lower_ir_program


def test_preview_text_strips_brackets():
    text = "Hello [world] {demo} (test)"
    assert preview_text(text) == "Hello world demo test"


def test_preview_text_redacts_sensitive():
    assert preview_text("my password is 123") == "redacted"


def test_link_limit_drops_oldest():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    item = factory.create(
        session="session:anon",
        kind=MemoryKind.SEMANTIC,
        text="alpha",
        source="user",
    )
    for idx in range(12):
        link = build_link_record(
            link_type=LINK_TYPE_REPLACED,
            to_id=f"id-{idx}",
            reason_code="replaced",
            created_in_phase_id="phase-1",
        )
        item = add_link_to_item(item, link, preview=f"preview {idx}")
    links = item.meta.get("links", [])
    assert len(links) == 10
    assert links[0]["to_id"] == "id-2"
    previews = item.meta.get("link_preview_text", {})
    assert "id-0" not in previews


def test_link_lines_and_path_lines_are_bracketless():
    factory = MemoryItemFactory(clock=MemoryClock(), id_generator=MemoryIdGenerator())
    item = factory.create(
        session="session:anon",
        kind=MemoryKind.SEMANTIC,
        text="alpha",
        source="user",
        meta={
            "links": [
                {
                    "type": "replaced",
                    "to_id": "session:anon:semantic:0",
                    "reason_code": "replaced",
                    "created_in_phase_id": "phase-1",
                }
            ],
            "link_preview_text": {"session:anon:semantic:0": "older item"},
        },
    )
    lines = link_lines(item) + path_lines(item)
    for line in lines:
        assert all(ch not in line for ch in "[]{}()")


def test_links_from_conflict_and_replacement():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is false
    profile is true
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    state: dict = {}
    memory.record_interaction_with_events(ai, state, "My name is Ada.", "ok", [])
    written, _events = memory.record_interaction_with_events(
        ai, state, "Actually, my name is Ada Lovelace.", "ok", []
    )
    profile_items = [item for item in written if item.get("kind") == "profile"]
    assert profile_items
    links = profile_items[0]["meta"].get("links", [])
    link_types = {link.get("type") for link in links}
    assert "conflicts_with" in link_types
    assert "replaced" in link_types
    replaced = next(link for link in links if link.get("type") == "replaced")
    preview = profile_items[0]["meta"].get("link_preview_text", {})
    assert replaced.get("to_id") in preview


def test_links_from_promotion():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is true
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    state: dict = {}
    written, _events = memory.record_interaction_with_events(
        ai, state, "Remember this for me: I prefer concise updates.", "ok", []
    )
    promoted = [item for item in written if item.get("meta", {}).get("space") == "user"]
    assert promoted
    links = promoted[0]["meta"].get("links", [])
    link_types = {link.get("type") for link in links}
    assert LINK_TYPE_PROMOTED_FROM in link_types
    assert LINK_TYPE_REPLACED in link_types


def test_links_from_summary_replacement():
    program = lower_ir_program(
        '''ai "assistant":
  provider is "mock"
  model is "mock-model"
  memory:
    short_term is 1
    semantic is false
    profile is false
'''
    )
    ai = program.ais["assistant"]
    memory = MemoryManager()
    state: dict = {}
    memory.record_interaction_with_events(ai, state, "First message", "ok", [])
    written, _events = memory.record_interaction_with_events(ai, state, "Second message", "ok", [])
    summaries = [item for item in written if item.get("meta", {}).get("summary_of")]
    assert summaries
    links = summaries[0]["meta"].get("links", [])
    link_types = {link.get("type") for link in links}
    assert LINK_TYPE_REPLACED in link_types
