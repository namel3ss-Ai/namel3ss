from pathlib import Path


TEMPLATE_ROOT = Path("src/namel3ss/templates")
TEMPLATES_WITH_AI = ["demo"]
EXPECTED_KEYS = [
    "N3_DEMO_PROVIDER=",
    "N3_DEMO_MODEL=",
    "NAMEL3SS_OPENAI_API_KEY=",
    "OPENAI_API_KEY=",
]


def test_templates_include_env_example_aliases() -> None:
    for template in TEMPLATES_WITH_AI:
        env_path = TEMPLATE_ROOT / template / ".env.example"
        assert env_path.exists()
        content = env_path.read_text(encoding="utf-8")
        for key in EXPECTED_KEYS:
            assert key in content
