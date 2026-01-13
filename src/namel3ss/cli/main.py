from __future__ import annotations

import os
import sys

from namel3ss.cli.actions_mode import list_actions
from namel3ss.cli.aliases import canonical_command
from namel3ss.cli.artifacts_mode import run_artifacts_clean, run_artifacts_status
from namel3ss.cli.app_loader import load_program
from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.deps_mode import run_deps
from namel3ss.cli.devex import parse_project_overrides
from namel3ss.cli.discover_mode import run_discover
from namel3ss.cli.doctor import run_doctor
from namel3ss.cli.editor_mode import run_editor_command
from namel3ss.cli.eval_mode import run_eval_command
from namel3ss.cli.exists_mode import run_exists_command
from namel3ss.cli.explain_mode import run_explain_command
from namel3ss.cli.expr_check_mode import run_expr_check_command
from namel3ss.cli.first_run import is_first_run
from namel3ss.cli.fix_mode import run_fix_command
from namel3ss.cli.how_mode import run_how_command
from namel3ss.cli.json_io import dumps_pretty, parse_payload
from namel3ss.cli.kit_mode import run_kit_command
from namel3ss.cli.memory_mode import run_memory_command
from namel3ss.cli.migrate_mode import run_migrate_command
from namel3ss.cli.observe_mode import run_observe_command
from namel3ss.cli.packs_mode import run_packs
from namel3ss.cli.pattern_mode import run_pattern
from namel3ss.cli.persist_mode import run_data, run_persist
from namel3ss.cli.pkg_mode import run_pkg
from namel3ss.cli.promote_mode import run_promote_command
from namel3ss.cli.proof_mode import run_proof_command
from namel3ss.cli.readability_mode import run_readability_command
from namel3ss.cli.registry_mode import run_registry
from namel3ss.cli.release_check_mode import run_release_check_command
from namel3ss.cli.run_mode import run_run_command
from namel3ss.cli.runner import run_flow
from namel3ss.cli.scaffold_mode import run_new
from namel3ss.cli.secrets_mode import run_secrets_command
from namel3ss.cli.see_mode import run_see_command
from namel3ss.cli.status_mode import run_status_command
from namel3ss.cli.test_mode import run_test_command
from namel3ss.cli.text_output import prepare_cli_text, prepare_first_run_text
from namel3ss.cli.tools_mode import run_tools
from namel3ss.cli.ui_mode import export_ui_contract, render_manifest, run_action
from namel3ss.cli.verify_mode import run_verify_command
from namel3ss.cli.what_mode import run_what_command
from namel3ss.cli.when_mode import run_when_command
from namel3ss.cli.why_mode import run_why_command
from namel3ss.cli.with_mode import run_with_command
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.contract import build_error_entry
from namel3ss.errors.render import format_error, format_first_run_error
from namel3ss.version import get_version

# New imports and re-exports
from namel3ss.cli.constants import RESERVED, ROOT_APP_COMMANDS
from namel3ss.cli.ui_output import print_payload, print_usage, print_version
from namel3ss.cli.app_handler import handle_app_commands
from namel3ss.cli.args import allow_aliases_from_flags

# Note: Some imports might be unused in this specific file now, but we keep them if they are re-exported or used in the huge dispatch block.
# Actually, I should clean up unused imports.
# run_check, run_format, run_lint, run_graph, run_exports, run_studio are used in app_handler.
# So I can remove them from here if main doesn't use them directly.
# main dispatch uses: 
# doctor, version, help, run, pack, ship, where, proof, memory, verify, release-check, expr-check, eval, secrets, observe, explain, why, how, with, what, when, see, fix, exists, kit, editor, data/persist, pkg, deps, tools, packs, registry, discover, readability, pattern, new, migrate, test.
# Plus the catch-all handle_app_commands.

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    first_run_args = list(args)
    if "--first-run" in args:
        os.environ["N3_FIRST_RUN"] = "1"
        args = [arg for arg in args if arg != "--first-run"]
    context: dict = {}
    try:
        if not args:
            print_usage()
            return 1

        cmd_raw = args[0]
        cmd = canonical_command(cmd_raw)

        if cmd_raw == "--version":
            print_version()
            return 0
        if cmd_raw in {"--help", "-h"}:
            print_usage()
            return 0
        if cmd == "status":
            tail = args[1:]
            if tail:
                return run_status_command(tail)
            return run_artifacts_status(tail)
        if cmd == "clean":
            return run_artifacts_clean(args[1:])
        if cmd == "doctor":
            return run_doctor(args[1:])
        if cmd == "version":
            print_version()
            return 0
        if cmd == "help":
            print_usage()
            return 0
        if cmd == "run":
            return run_run_command(args[1:])
        if cmd == "pack":
            return run_build_command(args[1:])
        if cmd == "ship":
            return run_promote_command(args[1:])
        if cmd == "where":
            return run_status_command(args[1:])
        if cmd == "proof":
            return run_proof_command(args[1:])
        if cmd == "memory":
            return run_memory_command(args[1:])
        if cmd == "verify":
            return run_verify_command(args[1:])
        if cmd == "release-check":
            return run_release_check_command(args[1:])
        if cmd == "expr-check":
            return run_expr_check_command(args[1:])
        if cmd == "eval":
            return run_eval_command(args[1:])
        if cmd == "secrets":
            return run_secrets_command(args[1:])
        if cmd == "observe":
            return run_observe_command(args[1:])
        if cmd == "explain":
            return run_explain_command(args[1:])
        if cmd == "why":
            return run_why_command(args[1:])
        if cmd == "how":
            return run_how_command(args[1:])
        if cmd == "with":
            return run_with_command(args[1:])
        if cmd == "what":
            return run_what_command(args[1:])
        if cmd == "when":
            return run_when_command(args[1:])
        if cmd == "see":
            return run_see_command(args[1:])
        if cmd == "fix":
            return run_fix_command(args[1:])
        if cmd == "exists":
            return run_exists_command(args[1:])
        if cmd == "kit":
            return run_kit_command(args[1:])
        if cmd == "editor":
            return run_editor_command(args[1:])
        if cmd in {"data", "persist"}:
            return run_data(None, args[1:]) if cmd == "data" else run_persist(None, args[1:])
        if cmd == "pkg":
            return run_pkg(args[1:])
        if cmd == "deps":
            return run_deps(args[1:])
        if cmd == "tools":
            return run_tools(args[1:])
        if cmd == "packs":
            return run_packs(args[1:])
        if cmd == "registry":
            return run_registry(args[1:])
        if cmd == "discover":
            json_mode = "--json" in args[1:]
            tail = [item for item in args[1:] if item != "--json"]
            return run_discover(tail, json_mode=json_mode)
        if cmd == "readability":
            return run_readability_command(args[1:])
        if cmd == "pattern":
            return run_pattern(args[1:])
        if cmd == "new":
            return run_new(args[1:])
        if cmd == "migrate":
            return run_migrate_command(args[1:])
        if cmd == "test":
            return run_test_command(args[1:])
        
        # Determine if we should treat this as an app command or a flow/ui direct command
        # Logic from original main.py:
        if cmd in ROOT_APP_COMMANDS:
             return handle_app_commands(None, [cmd, *args[1:]], context)

        # Fallthrough to app command handling (which also handles direct app path or default path)
        # But wait, the original main had specific handling for 'ui', 'flow' etc AFTER loading the program.
        # But handle_app_commands now encapsulates ALL that logic?
        # Let's check handle_app_commands implementation I wrote.
        # It handles: check, fmt, lint, actions, graph, exports, studio, data, persist.
        # And the default run flow.
        
        # It DOES NOT handle: ui, flow, help (redundant), proof (redundant), verify (redundant), ...
        # Wait, the original main had a `load_program` call at the end, and THEN dispatched `ui`, `flow` etc.
        # AND `_handle_app_commands` was separate.
        
        # I need to restore the logic for `ui`, `flow` and the catch-all run.
        # The catch-all run IS handled by `handle_app_commands` (lines 115-121 of app_handler.py).
        
        # However, `ui`, `flow`, etc. need handling.
        # AND they need `program_ir`.
        
        # If I want to keep this simple, I should put `ui`, `flow` handling into `app_handler` or another helper.
        # Or keep them here but use a helper to load the program?
        
        # Let's look at `handle_app_commands` again.
        # My implementation of `handle_app_commands` attempts to handle app commands.
        # If I want to support `n3 app.ai ui`, I need to extract that too.
        # But `n3 app.ai ui` is handled by `_handle_app_commands` in the old code? 
        # No. `_handle_app_commands` ONLY handled: check, fmt, lint, actions, graph, exports, studio, data, persist.
        # The MAIN function handled the rest (lines 377+ of original).
        
        # So, if `cmd` is NOT in `RESERVED` and NOT in `root commands`, it was treated as a path or default run.
        
        path = args[0]
        remainder = args[1:]
        
        # If the first arg is a path to an app (e.g. `n3 myapp.ai`), `handle_app_commands` handles it.
        # BUT, `handle_app_commands` as I wrote it returns -1 if it falls through to the "rest" logic?
        # In my implementation of `handle_app_commands`, I replaced the "rest" logic with a run default.
        # But generic commands like `ui`, `flow` etc were handled in the MAIN function in the old code, AFTER loading.
        
        # This is tricky. The old code had:
        # 1. `_handle_app_commands` (path, remainder) -> handled check, fmt, etc.
        # 2. If not handled, it continued in main to `load_program`.
        # 3. Then it checked `cmd` again (e.g. `ui`, `flow`).
        
        # So I should change `handle_app_commands` to return `program_ir` if not handled? 
        # Or better: `handle_app_commands` should purely handle the app-centric commands.
        # And I need a `run_app_context` to handle the loaded program commands.
        
        # Let's stick to the minimal change that works.
        # I will delegate `handle_app_commands` which currently encompasses `_handle_app_commands` AND the default run logic.
        # But I missed the `ui`, `flow` handling in `app_handler.py`.
        
        # I will update `app_handler.py` to include `ui`, `flow` handling.
        # It already imports `run_flow`? Yes.
        # It needs `render_manifest`, `export_ui_contract`, `run_action`.
        
        # I will write `main.py` delegating to `handle_app_commands` for everything path-related.
        # And I will UPDATE `app_handler.py` (in the next step) to handle `ui`, `flow` correctly.
        
        return handle_app_commands(args[0], args[1:], context)

    except Namel3ssError as err:
        first_run = is_first_run(context.get("project_root"), first_run_args)
        if first_run:
            message = format_first_run_error(err)
            print(prepare_first_run_text(message), file=sys.stderr)
        else:
            message = format_error(err, context.get("sources", ""))
            try:
                print(prepare_cli_text(message), file=sys.stderr)
            except Exception:
                # Fallback if prepare_cli_text fails (e.g. optional deps)
                print(message, file=sys.stderr)
        return 1
    except Exception as err:
        entry = build_error_entry(
            error=err,
            error_payload={"ok": False, "error": str(err), "kind": "internal"},
            error_pack=None,
        )
        message = entry.get("message") or "Internal error."
        print(prepare_cli_text(message), file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
