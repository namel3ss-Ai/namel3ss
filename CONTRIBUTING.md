# Contributing to Namel3ss

This project is GA-focused: clarity, determinism, and backward compatibility come first.

## Contribution standards

- Keep behavior explicit and deterministic.
- Preserve public APIs unless an RFC explicitly changes them.
- Keep each file under 500 lines and split around 450 lines.
- Keep one responsibility per file.
- Use descriptive file names; avoid placeholders and version suffixes.

## Branch and PR workflow

1. Open an issue or RFC for substantial changes.
2. Create a focused branch.
3. Add tests for every behavioral change.
4. Update docs when contracts or UX change.
5. Submit a PR with a clear scope and migration impact.

## Required checks

Run locally before opening a PR:

```bash
python -m compileall src -q
python -m pytest -q
python tools/line_limit_check.py
python tools/responsibility_check.py
python -m namel3ss.beta_lock.repo_clean
```

## Public vs internal APIs

- Public APIs are declared in `src/namel3ss/lang/public_api.py`.
- Internal APIs are declared in `src/namel3ss/lang/internal_api.py`.
- Plugins and apps must not import internal modules.

## Compatibility and deprecation

- Follow semantic versioning and compatibility rules in `docs/compatibility_policy.md`.
- Follow deprecation policy in `docs/deprecation_policy.md`.
- New deprecations must include deterministic warnings and migration instructions.

## Security reporting

Do not open public issues for vulnerabilities.
Use `SECURITY.md` for private reporting instructions.

## Review expectations

- Small, focused PRs are preferred.
- Contract changes require two maintainer reviews.
- Governance, security, and release process changes require LSC review.

## Commit message format

Use scoped, descriptive messages:

- `lang: add deprecation warning for ui_theme capability`
- `release: add deterministic GA checklist script`
- `docs: publish compatibility and deprecation policies`

## RFC requirement

RFCs are required for:

- grammar or syntax changes
- public API changes
- manifest schema changes
- compatibility policy changes
- release governance changes

See `RFC_PROCESS.md` for details.
