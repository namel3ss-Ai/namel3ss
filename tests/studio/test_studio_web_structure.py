from pathlib import Path


def test_studio_html_structure():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "namel3ss Studio" in html
    for label in ["Graph", "Traces", "Memory", "Why"]:
        assert label in html
    for label in [
        "Summary",
        "Trust",
        "Rules",
        "Handoff",
        "Data",
        "Fix",
        "State",
        "Actions",
        "Tools",
        "Packs",
        "Packages",
        "Discover",
        "Security",
        "Lint",
        "Inspector",
        "Help",
        "Learn",
    ]:
        assert label not in html
    for element_id in [
        "run",
        "ui",
        "traces",
        "tracesFilter",
        "memory",
        "why",
        "dock",
        "sheet",
        "sheetBackdrop",
        "toast",
    ]:
        assert f'id="{element_id}"' in html
    assert "pageSelect" not in html
    assert "preview-header" not in html
    assert "Run ▸" in html
    assert html.count('class="btn primary') == 1
    assert "studio-panels" not in html
    for removed_id in ["themeSelect", "toolWizardButton", "reset", "helpButton", "learnToggle", "versionLabel"]:
        assert f'id="{removed_id}"' not in html


def test_studio_run_button_state_logic():
    js = Path("src/namel3ss/studio/web/app/setup/buttons.js").read_text(encoding="utf-8")
    assert "runButton.disabled = true" in js
    assert "Running…" in js
    assert "Couldn't run." in js


def test_studio_traces_timeline_rendering():
    js = Path("src/namel3ss/studio/web/app/traces/render.js").read_text(encoding="utf-8")
    assert "Run Timeline" in js
    assert "trace-summary" in js
    assert "trace-toggle" in js
    assert "createCodeBlock" not in js
    assert "appendTraceSection" not in js


def test_studio_memory_panel_structure():
    js = Path("src/namel3ss/studio/web/app/render/memory.js").read_text(encoding="utf-8")
    assert "Recalled" in js
    assert "Written" in js
    assert "createCodeBlock" not in js
    for label in ["Approve", "Reject", "Propose", "Pack"]:
        assert label not in js


def test_studio_why_panel_structure():
    js = Path("src/namel3ss/studio/web/app/render/why.js").read_text(encoding="utf-8")
    assert "Run your app to see why it behaved the way it did." in js
    for heading in ["What happened", "Why", "What didn't happen"]:
        assert heading in js
    assert "why-list" in js
    assert "createCodeBlock" not in js
    for label in ["settings", "config", "editor"]:
        assert label not in js.lower()


def test_studio_empty_state_copy():
    ui = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    traces = Path("src/namel3ss/studio/web/app/traces/render.js").read_text(encoding="utf-8")
    memory = Path("src/namel3ss/studio/web/app/render/memory.js").read_text(encoding="utf-8")
    assert "Run your app to see it here." in ui
    assert "No traces yet. Run your app." in traces
    assert "No memory events yet. Run your app." in memory


def test_studio_error_state_copy():
    js = Path("src/namel3ss/studio/web/app/utils/dom.js").read_text(encoding="utf-8")
    for line in ["Couldn't run.", "What happened:", "Try: Run again."]:
        assert line in js
    assert "renderStatusLines(container, buildErrorLines" in js
    assert "traceback" in js.lower()
    assert 'text.startsWith("{")' in js
    assert 'text.startsWith("[")' in js
