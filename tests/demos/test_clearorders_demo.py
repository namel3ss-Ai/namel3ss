from __future__ import annotations

from pathlib import Path
import re
import socket
import pytest

from namel3ss.cli.main import main as cli_main
from namel3ss.cli.app_loader import load_program
from namel3ss.runtime.executor import execute_program_flow
from namel3ss.runtime.service_runner import ServiceRunner
from namel3ss.runtime.store.memory_store import MemoryStore
from namel3ss.ui.manifest import build_manifest

FORBIDDEN_TERMS = ("ir", "contract", "capability", "policy", "determinism", "pack", "schema")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _template_root() -> Path:
    return _repo_root() / "src" / "namel3ss" / "templates" / "clear_orders"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("0.0.0.0", 0))
        return int(sock.getsockname()[1])


def _flatten_elements(elements: list[dict]) -> list[dict]:
    flattened: list[dict] = []
    for element in elements:
        flattened.append(element)
        if element.get("children"):
            flattened.extend(_flatten_elements(element["children"]))
    return flattened


def _page_by_name(manifest: dict, name: str) -> dict | None:
    for page in manifest.get("pages", []):
        if page.get("name") == name:
            return page
    return None


def _table_rows(manifest: dict, record_name: str) -> list[dict]:
    for page in manifest.get("pages", []):
        for element in _flatten_elements(page.get("elements", [])):
            if element.get("type") == "table" and element.get("record") == record_name:
                return element.get("rows", [])
    return []


def _build_demo_bullets(stats: list[dict]) -> list[str]:
    mapped = {row.get("key"): row for row in stats if row.get("key")}
    bullets: list[str] = []
    orders = mapped.get("orders_reviewed", {}).get("value_number")
    top_region = mapped.get("top_region", {}).get("value_text")
    top_returns = mapped.get("top_region_returns", {}).get("value_number")
    avg_delivery = mapped.get("avg_delivery_days", {}).get("value_number")
    avg_satisfaction = mapped.get("avg_satisfaction", {}).get("value_number")
    fallback_text = mapped.get("fallback", {}).get("value_text")

    if orders is not None:
        bullets.append(f"Reviewed {orders} orders to answer your question.")
    if top_region and top_returns is not None:
        bullets.append(f"Highest returns are in {top_region} with {top_returns} returns.")
    if avg_delivery is not None:
        bullets.append(f"Average delivery time on returned orders is {avg_delivery} days.")
    if avg_satisfaction is not None:
        bullets.append(f"Average satisfaction on returned orders is {avg_satisfaction} out of 5.")
    if fallback_text:
        bullets.insert(0, str(fallback_text))

    defaults = [
        "The answer is based on the orders shown on this page.",
        "Returns and delivery time patterns shape the summary.",
        "The data highlights where returns cluster most often.",
    ]
    for line in defaults:
        if len(bullets) >= 3:
            break
        bullets.append(line)
    return bullets


def _assert_no_forbidden_terms(text: str) -> None:
    for term in FORBIDDEN_TERMS:
        pattern = re.compile(rf"\\b{re.escape(term)}\\b", re.IGNORECASE)
        assert not pattern.search(text)


def test_clearorders_template_scaffolds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code = cli_main(["new", "demo"])
    assert code == 0
    project_dir = tmp_path / "demo"
    assert (project_dir / "app.ai").exists()
    assert (project_dir / "namel3ss.toml").exists()
    assert (project_dir / ".namel3ss" / "demo.json").exists()
    assert (project_dir / "ui" / "index.html").exists()
    assert (project_dir / "ui" / "app.js").exists()
    assert (project_dir / "ui" / "styles.css").exists()


def test_clearorders_ui_manifest_elements():
    app_path = _template_root() / "app.ai"
    program, _ = load_program(str(app_path))
    store = MemoryStore()
    execute_program_flow(program, "seed_orders", store=store)
    manifest = build_manifest(program, state={}, store=store)
    home = _page_by_name(manifest, "home")
    assert home
    elements = _flatten_elements(home.get("elements", []))
    titles = [element.get("value") for element in elements if element.get("type") == "title"]
    assert "ClearOrders" in titles
    tables = {element.get("record") for element in elements if element.get("type") == "table"}
    assert "Order" in tables
    assert "Answer" in tables
    assert "ExplanationStat" in tables
    sections = {element.get("label") for element in elements if element.get("type") == "section"}
    assert "Orders (12)" in sections
    orders = _table_rows(manifest, "Order")
    assert len(orders) == 12
    buttons = {element.get("label") for element in elements if element.get("type") == "button"}
    assert "Ask AI" in buttons
    assert "Why?" in buttons

    labels = " ".join(str(label or "") for label in buttons | set(titles) | sections)
    _assert_no_forbidden_terms(labels)


def test_clearorders_intro_page_copy():
    app_path = _template_root() / "app.ai"
    program, _ = load_program(str(app_path))
    manifest = build_manifest(program, state={}, store=MemoryStore())
    intro = _page_by_name(manifest, "intro")
    assert intro
    elements = _flatten_elements(intro.get("elements", []))
    titles = [element.get("value") for element in elements if element.get("type") == "title"]
    assert "ClearOrders" in titles
    texts = [element.get("value") for element in elements if element.get("type") == "text"]
    assert "A demo you can trust." in texts
    assert "A small dataset... A human explanation." in texts
    assert "You get the data, the answer, and the reasoning in one place." in " ".join(texts)
    labels = {element.get("label") for element in elements if element.get("label")}
    assert "What you see" in labels
    assert "Why it matters" in labels
    assert "Get started" in labels
    assert "Open demo" in labels
    combined = " ".join([*texts, *labels])
    _assert_no_forbidden_terms(combined)


def test_clearorders_get_started_page_copy():
    app_path = _template_root() / "app.ai"
    program, _ = load_program(str(app_path))
    manifest = build_manifest(program, state={}, store=MemoryStore())
    get_started = _page_by_name(manifest, "get_started")
    assert get_started
    elements = _flatten_elements(get_started.get("elements", []))
    labels = {element.get("label") for element in elements if element.get("label")}
    assert "Install" in labels
    assert "Run the demo" in labels
    assert "Open Studio (optional)" in labels
    assert "Back" in labels
    assert "Open demo" in labels
    texts = [element.get("value") for element in elements if element.get("type") == "text"]
    assert "$ pip install namel3ss" in texts
    assert "$ n3 new demo && cd demo && n3 run" in texts
    assert "$ n3 app.ai studio" in texts
    combined = " ".join([*texts, *labels])
    _assert_no_forbidden_terms(combined)


def test_clearorders_answer_and_explanation():
    app_path = _template_root() / "app.ai"
    program, _ = load_program(str(app_path))
    store = MemoryStore()
    execute_program_flow(program, "seed_orders", store=store)
    execute_program_flow(
        program,
        "ask_ai",
        store=store,
        input={"values": {"question": "Which region has the most returns?"}},
    )
    execute_program_flow(program, "why_answer", store=store)
    manifest = build_manifest(program, state={}, store=store)
    answers = _table_rows(manifest, "Answer")
    stats = _table_rows(manifest, "ExplanationStat")
    orders = _table_rows(manifest, "Order")

    assert answers
    answer_text = str(answers[-1].get("text") or "")
    assert answer_text.strip()
    _assert_no_forbidden_terms(answer_text)

    assert len(stats) >= 3
    stats_text = " ".join(str(row.get("value_text") or "") for row in stats)
    _assert_no_forbidden_terms(stats_text)
    bullets = _build_demo_bullets(stats)
    assert len(bullets) >= 3
    for bullet in bullets:
        _assert_no_forbidden_terms(bullet)

    returned = [row for row in orders if row.get("returned") is True]
    returns_by_region: dict[str, int] = {}
    for row in returned:
        region = row.get("region")
        if not region:
            continue
        returns_by_region[str(region)] = returns_by_region.get(str(region), 0) + 1
    top_region, top_returns = sorted(returns_by_region.items(), key=lambda item: (-item[1], item[0]))[0]
    avg_delivery = sum(row.get("delivery_days", 0) for row in returned) / len(returned)
    avg_satisfaction = sum(row.get("satisfaction", 0) for row in returned) / len(returned)

    mapped = {row.get("key"): row for row in stats}
    assert mapped["orders_reviewed"]["value_number"] == len(orders)
    assert mapped["top_region"]["value_text"] == top_region
    assert mapped["top_region_returns"]["value_number"] == top_returns
    assert mapped["avg_delivery_days"]["value_number"] == pytest.approx(avg_delivery)
    assert mapped["avg_satisfaction"]["value_number"] == pytest.approx(avg_satisfaction)


def test_clearorders_ui_copy_avoids_forbidden_terms():
    template_root = _template_root()
    ui_text = (template_root / "ui" / "index.html").read_text(encoding="utf-8")
    app_text = (template_root / "ui" / "app.js").read_text(encoding="utf-8")
    _assert_no_forbidden_terms(ui_text)
    _assert_no_forbidden_terms(app_text)


def test_clearorders_seed_patterns():
    app_path = _template_root() / "app.ai"
    program, _ = load_program(str(app_path))
    store = MemoryStore()
    execute_program_flow(program, "seed_orders", store=store)
    manifest = build_manifest(program, state={}, store=store)
    orders = _table_rows(manifest, "Order")

    west_returns = [
        row
        for row in orders
        if row.get("region") == "West" and row.get("returned") is True
    ]
    assert len(west_returns) == 4
    assert all((row.get("delivery_days") or 0) >= 5 for row in west_returns)
    assert all((row.get("satisfaction") or 0) <= 2 for row in west_returns)

    express_low_sat = [
        row
        for row in orders
        if row.get("shipping") == "Express" and (row.get("satisfaction") or 0) <= 2
    ]
    assert len(express_low_sat) == 2


def test_clearorders_run_prints_url(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli_main(["new", "demo"]) == 0
    capsys.readouterr()
    project_dir = tmp_path / "demo"
    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(ServiceRunner, "start", lambda *args, **kwargs: None)
    port = _free_port()
    code = cli_main(["run", "--port", str(port)])
    out = capsys.readouterr().out.strip().splitlines()
    assert code == 0
    assert out == [
        "Running ClearOrders",
        f"Open: http://127.0.0.1:{port}/",
        "Press Ctrl+C to stop",
    ]
