from pathlib import Path


TEMPLATE_ROOT = Path("src/namel3ss/templates")


def test_templates_do_not_ship_env_example() -> None:
    env_examples = sorted(TEMPLATE_ROOT.glob("*/.env.example"))
    assert env_examples == []
