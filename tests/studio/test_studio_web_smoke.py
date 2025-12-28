from pathlib import Path


def _app_bundle():
    app_root = Path("src/namel3ss/studio/web/app")
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(app_root.rglob("*.js")))


def test_studio_html_structure():
    html = Path("src/namel3ss/studio/web/index.html").read_text(encoding="utf-8")
    assert "Namel3ss Studio" in html
    for label in [
        "Summary",
        "Graph",
        "Trust",
        "Rules",
        "Handoff",
        "Data & Identity",
        "Guided Fixes",
        "Packages",
        "State",
        "Actions",
        "Security",
        "Traces",
        "Lint Findings",
        "UI Preview",
    ]:
        assert label in html
    assert 'id="traces"' in html
    assert 'id="tracesFilter"' in html
    assert "Filter traces…" in html
    assert 'id="traceFormatPlain"' in html
    assert 'id="traceFormatJson"' in html
    assert 'id="tracePhaseCurrent"' in html
    assert 'id="tracePhaseHistory"' in html
    assert 'id="traceLaneMy"' in html
    assert 'id="traceLaneTeam"' in html
    assert 'id="traceLaneSystem"' in html
    assert 'id="teamAgreements"' in html
    assert 'id="teamAgreementsList"' in html
    assert 'id="teamAgreementSummary"' in html
    assert 'id="teamTrust"' in html
    assert 'id="teamTrustLines"' in html
    assert 'id="teamTrustNotice"' in html
    assert 'id="rulesPanel"' in html
    assert 'id="rulesActiveTeam"' in html
    assert 'id="rulesActiveSystem"' in html
    assert 'id="rulesPendingTeam"' in html
    assert 'id="rulesPendingSystem"' in html
    assert 'id="handoffPanel"' in html
    assert 'id="handoffAgents"' in html
    assert 'id="handoffPackets"' in html
    assert 'id="handoffFrom"' in html
    assert 'id="handoffTo"' in html
    assert 'id="handoffCreate"' in html
    assert 'id="addElementButton"' in html
    assert 'id="inspectorBody"' in html
    assert 'id="learnToggle"' in html
    app_js = _app_bundle()
    assert "memory_explanation" in app_js
    assert "memory_links" in app_js
    assert "memory_path" in app_js
    assert "memory_impact" in app_js
    assert "memory_change_preview" in app_js
    assert "memory_team_summary" in app_js
    assert "memory_proposed" in app_js
    assert "memory_approved" in app_js
    assert "memory_rejected" in app_js
    assert "memory_agreement_summary" in app_js
    assert "memory_trust_check" in app_js
    assert "memory_approval_recorded" in app_js
    assert "memory_trust_rules" in app_js
    assert "memory_rule_applied" in app_js
    assert "memory_rules_snapshot" in app_js
    assert "memory_rule_changed" in app_js
    assert "Explain" in app_js
    assert "Links" in app_js
    assert "Path" in app_js
    assert "Impact" in app_js
    assert "Approve" in app_js
    assert "Reject" in app_js
    renderer_js = Path("src/namel3ss/studio/web/ui_renderer.js").read_text(encoding="utf-8")
    for token in ['el.type === "section"', 'el.type === "card"', 'el.type === "row"', 'el.type === "column"', 'el.type === "divider"', 'el.type === "image"']:
        assert token in renderer_js
