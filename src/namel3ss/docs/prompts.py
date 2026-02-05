from __future__ import annotations


def collect_prompts(program) -> list[dict]:
    prompts = []
    for prompt in getattr(program, "prompts", []) or []:
        prompts.append(
            {
                "name": prompt.name,
                "version": prompt.version,
                "text": prompt.text,
                "description": prompt.description,
            }
        )
    prompts.sort(key=lambda item: item["name"])
    return prompts


__all__ = ["collect_prompts"]
