from namel3ss.ast import nodes as ast


def test_facade_exports_representative_symbols() -> None:
    expected = [
        "Program",
        "Flow",
        "Let",
        "If",
        "Literal",
        "PageDecl",
        "AIDecl",
        "AgentDecl",
        "RunAgentsParallelStmt",
    ]
    for name in expected:
        assert hasattr(ast, name), f"nodes missing {name}"
        attr = getattr(ast, name)
        assert hasattr(attr, "__dataclass_fields__")
