from pathlib import Path


def test_studio_html_structure():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "namel3ss Studio" in html
    assert "/studio/guidance.js" in html
    assert "/studio/explain.js" in html
    assert "/studio/agents/index.js" in html
    assert "/studio/agents/wizard.js" in html
    guidance_idx = html.index("/studio/guidance.js")
    dom_idx = html.index("/studio/dom.js")
    action_result_idx = html.index("/studio/action_result.js")
    errors_idx = html.index("/studio/errors.js")
    run_idx = html.index("/studio/run.js")
    assert guidance_idx < dom_idx < errors_idx
    assert action_result_idx < run_idx
    for label in [
        "Preview",
        "Why",
        "Data",
        "Errors",
        "Formulas",
        "Explain",
        "Traces",
        "Memory",
        "Agents",
        "Setup",
        "Graph",
    ]:
        assert label in html
    for label in [
        "Summary",
        "Trust",
        "Rules",
        "Handoff",
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
        "aiModeBadge",
        "aiModeBadgeText",
        "aiModeBadgeSetup",
        "previewQuestion",
        "previewAsk",
        "previewAnswer",
        "previewWhy",
        "errors",
        "formulas",
        "explain",
        "errorBanner",
        "traces",
        "tracesFilter",
        "memory",
        "agents",
        "setup",
        "setupBanner",
        "why",
        "data",
        "dock",
        "dock-errors",
        "dock-formulas",
        "dock-explain",
        "dock-agents",
        "studioMenu",
        "toast",
        "secretsModal",
    ]:
        assert f'id="{element_id}"' in html
    assert "pageSelect" not in html
    assert "preview-header" not in html
    assert "Run ▸" in html
    assert html.count('class="btn primary') >= 2
    assert "studio-panels" not in html
    for removed_id in ["themeSelect", "toolWizardButton", "reset", "helpButton", "learnToggle", "versionLabel"]:
        assert f'id="{removed_id}"' not in html


def test_studio_run_button_state_logic():
    js = Path("src/namel3ss/studio/web/studio/run.js").read_text(encoding="utf-8")
    assert "button.disabled = true" in js
    assert "Running..." in js
    assert "Run complete." in js
    assert "applyActionResult" in js


def test_studio_traces_timeline_rendering():
    js = Path("src/namel3ss/studio/web/studio/traces.js").read_text(encoding="utf-8")
    assert "No traces yet. Run your app." in js
    assert "trace-summary" in js
    assert "trace-toggle" in js
    assert "createCodeBlock" not in js
    assert "appendTraceSection" not in js


def test_studio_memory_panel_structure():
    js = Path("src/namel3ss/studio/web/studio/memory.js").read_text(encoding="utf-8")
    assert "Read-only memory" in js
    assert "Recent memory" in js
    assert "createCodeBlock" not in js
    for label in ["Approve", "Reject", "Propose", "Pack"]:
        assert label not in js


def test_studio_why_panel_structure():
    js = Path("src/namel3ss/studio/web/studio/why.js").read_text(encoding="utf-8")
    assert "Why this app is safe to run." in js
    assert "Summary" in js
    for heading in ["Execution environment", "Access rules", "Run summary"]:
        assert heading not in js
    assert "why-list" in js
    assert "createCodeBlock" not in js
    for label in ["settings", "config", "editor"]:
        assert label not in js.lower()


def test_studio_empty_state_copy():
    ui = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    traces = Path("src/namel3ss/studio/web/studio/traces.js").read_text(encoding="utf-8")
    memory = Path("src/namel3ss/studio/web/studio/memory.js").read_text(encoding="utf-8")
    assert "Run your app to see it here." in ui
    assert "No traces yet. Run your app." in traces
    assert "No memory events yet. Run your app." in memory


def test_studio_error_state_copy():
    js = Path("src/namel3ss/studio/web/studio/dom.js").read_text(encoding="utf-8")
    for line in ["Couldn't run.", "What happened:", "Try: Run again."]:
        assert line in js
    assert "buildErrorLines" in js
    assert "buildStatusLines" in js


def test_studio_boot_checks_render_ui_before_refresh():
    js = Path("src/namel3ss/studio/web/app.js").read_text(encoding="utf-8")
    assert "renderUI" in js
    assert "refreshUI" in js
    assert js.find("typeof window.renderUI") < js.find("root.refresh.refreshUI()")


def test_studio_codeblock_renderer():
    js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    assert "n3-codeblock" in js
    assert 'startsWith("$ ")' in js
    css = Path("src/namel3ss/studio/web/styles.css").read_text(encoding="utf-8")
    assert ".n3-codeblock" in css
