from pathlib import Path


TEMPLATE_ROOT = Path("src/namel3ss/templates")
TEMPLATES_WITH_AI = ["ai_assistant", "clear_orders", "multi_agent"]
EXPECTED_KEYS = [
    "NAMEL3SS_OPENAI_API_KEY=",
    "OPENAI_API_KEY=",
    "NAMEL3SS_ANTHROPIC_API_KEY=",
    "ANTHROPIC_API_KEY=",
    "NAMEL3SS_GEMINI_API_KEY=",
    "GEMINI_API_KEY=",
    "GOOGLE_API_KEY=",
    "NAMEL3SS_MISTRAL_API_KEY=",
    "MISTRAL_API_KEY=",
]


def test_templates_include_env_example_aliases() -> None:
    for template in TEMPLATES_WITH_AI:
        env_path = TEMPLATE_ROOT / template / ".env.example"
        assert env_path.exists()
        content = env_path.read_text(encoding="utf-8")
        for key in EXPECTED_KEYS:
            assert key in content
