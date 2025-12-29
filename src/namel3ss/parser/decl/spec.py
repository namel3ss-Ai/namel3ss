from __future__ import annotations


def parse_spec_decl(parser) -> str:
    parser._advance()
    parser._expect("IS", "Expected 'is' after spec.")
    value = parser._expect("STRING", "Expected a quoted spec version.").value
    return str(value or "").strip()


__all__ = ["parse_spec_decl"]
