from __future__ import annotations

import os
import sys

from namel3ss.cli.aliases import canonical_command
from namel3ss.cli.constants import ROOT_APP_COMMANDS
from namel3ss.cli.ui_output import print_usage, print_version
from namel3ss.errors.base import Namel3ssError

PACK_SUBCOMMANDS = {
    "list",
    "info",
    "add",
    "init",
    "validate",
    "review",
    "bundle",
    "sign",
    "remove",
    "status",
    "verify",
    "enable",
    "disable",
    "keys",
}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else list(argv)
    first_run_args = list(args)
    if "--first-run" in args:
        os.environ["N3_FIRST_RUN"] = "1"
        args = [arg for arg in args if arg != "--first-run"]
    if "--profile" in args:
        os.environ["N3_PROFILE"] = "1"
        args = [arg for arg in args if arg != "--profile"]
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
        if cmd == "reserved":
            from namel3ss.cli.reserved_mode import run_reserved_command

            return run_reserved_command(args[1:])
        if cmd == "icons":
            from namel3ss.cli.icons_mode import run_icons_command

            return run_icons_command(args[1:])
        if cmd == "status":
            tail = args[1:]
            if tail:
                from namel3ss.cli.status_mode import run_status_command

                return run_status_command(tail)
            from namel3ss.cli.artifacts_mode import run_artifacts_status

            return run_artifacts_status(tail)
        if cmd == "clean":
            from namel3ss.cli.artifacts_mode import run_artifacts_clean

            return run_artifacts_clean(args[1:])
        if cmd == "doctor":
            from namel3ss.cli.doctor import run_doctor

            return run_doctor(args[1:])
        if cmd == "version":
            print_version()
            return 0
        if cmd == "help":
            print_usage()
            return 0
        if cmd == "run":
            from namel3ss.cli.run_mode import run_run_command

            return run_run_command(args[1:])
        if cmd == "dev":
            from namel3ss.cli.browser_mode import run_dev_command

            return run_dev_command(args[1:])
        if cmd == "preview":
            from namel3ss.cli.browser_mode import run_preview_command

            return run_preview_command(args[1:])
        if cmd == "start":
            from namel3ss.cli.start_mode import run_start_command

            return run_start_command(args[1:])
        if cmd == "pack":
            if args[1:]:
                next_token = canonical_command(args[1])
                if next_token in PACK_SUBCOMMANDS:
                    from namel3ss.cli.packs_mode import run_packs

                    return run_packs(args[1:])
            from namel3ss.cli.build_mode import run_build_command

            return run_build_command(args[1:])
        if cmd == "ship":
            from namel3ss.cli.promote_mode import run_promote_command

            return run_promote_command(args[1:])
        if cmd == "where":
            from namel3ss.cli.status_mode import run_status_command

            return run_status_command(args[1:])
        if cmd == "proof":
            from namel3ss.cli.proof_mode import run_proof_command

            return run_proof_command(args[1:])
        if cmd == "memory":
            from namel3ss.cli.memory_mode import run_memory_command

            return run_memory_command(args[1:])
        if cmd == "verify":
            from namel3ss.cli.verify_mode import run_verify_command

            return run_verify_command(args[1:])
        if cmd == "release-check":
            from namel3ss.cli.release_check_mode import run_release_check_command

            return run_release_check_command(args[1:])
        if cmd == "expr-check":
            from namel3ss.cli.expr_check_mode import run_expr_check_command

            return run_expr_check_command(args[1:])
        if cmd == "eval":
            from namel3ss.cli.eval_mode import run_eval_command

            return run_eval_command(args[1:])
        if cmd == "secrets":
            from namel3ss.cli.secrets_mode import run_secrets_command

            return run_secrets_command(args[1:])
        if cmd == "observe":
            from namel3ss.cli.observe_mode import run_observe_command

            return run_observe_command(args[1:])
        if cmd == "explain":
            from namel3ss.cli.explain_mode import run_explain_command

            return run_explain_command(args[1:])
        if cmd == "why":
            from namel3ss.cli.why_mode import run_why_command

            return run_why_command(args[1:])
        if cmd == "how":
            from namel3ss.cli.how_mode import run_how_command

            return run_how_command(args[1:])
        if cmd == "with":
            from namel3ss.cli.with_mode import run_with_command

            return run_with_command(args[1:])
        if cmd == "what":
            from namel3ss.cli.what_mode import run_what_command

            return run_what_command(args[1:])
        if cmd == "when":
            from namel3ss.cli.when_mode import run_when_command

            return run_when_command(args[1:])
        if cmd == "see":
            from namel3ss.cli.see_mode import run_see_command

            return run_see_command(args[1:])
        if cmd == "fix":
            from namel3ss.cli.fix_mode import run_fix_command

            return run_fix_command(args[1:])
        if cmd == "exists":
            from namel3ss.cli.exists_mode import run_exists_command

            return run_exists_command(args[1:])
        if cmd == "kit":
            from namel3ss.cli.kit_mode import run_kit_command

            return run_kit_command(args[1:])
        if cmd == "editor":
            from namel3ss.cli.editor_mode import run_editor_command

            return run_editor_command(args[1:])
        if cmd in {"data", "persist"}:
            from namel3ss.cli.persist_mode import run_data, run_persist

            return run_data(None, args[1:]) if cmd == "data" else run_persist(None, args[1:])
        if cmd == "pkg":
            from namel3ss.cli.pkg_mode import run_pkg

            return run_pkg(args[1:])
        if cmd == "deps":
            from namel3ss.cli.deps_mode import run_deps

            return run_deps(args[1:])
        if cmd == "tools":
            from namel3ss.cli.tools_mode import run_tools

            return run_tools(args[1:])
        if cmd == "packs":
            from namel3ss.cli.packs_mode import run_packs

            return run_packs(args[1:])
        if cmd == "registry":
            from namel3ss.cli.registry_mode import run_registry

            return run_registry(args[1:])
        if cmd == "discover":
            from namel3ss.cli.discover_mode import run_discover

            json_mode = "--json" in args[1:]
            tail = [item for item in args[1:] if item != "--json"]
            return run_discover(tail, json_mode=json_mode)
        if cmd == "readability":
            from namel3ss.cli.readability_mode import run_readability_command

            return run_readability_command(args[1:])
        if cmd == "pattern":
            from namel3ss.cli.pattern_mode import run_pattern

            return run_pattern(args[1:])
        if cmd == "new":
            from namel3ss.cli.scaffold_mode import run_new

            return run_new(args[1:])
        if cmd == "migrate":
            from namel3ss.cli.migrate_mode import run_migrate_command

            return run_migrate_command(args[1:])
        if cmd == "test":
            from namel3ss.cli.test_mode import run_test_command

            return run_test_command(args[1:])
        if cmd in ROOT_APP_COMMANDS:
            from namel3ss.cli.app_handler import handle_app_commands

            return handle_app_commands(None, [cmd, *args[1:]], context)

        from namel3ss.cli.app_handler import handle_app_commands

        return handle_app_commands(args[0], args[1:], context)

    except Namel3ssError as err:
        from namel3ss.cli.first_run import is_first_run
        from namel3ss.cli.text_output import prepare_cli_text, prepare_first_run_text
        from namel3ss.errors.render import format_error, format_first_run_error

        first_run = is_first_run(context.get("project_root"), first_run_args)
        if first_run:
            message = format_first_run_error(err)
            print(prepare_first_run_text(message), file=sys.stderr)
        else:
            message = format_error(err, context.get("sources", ""))
            try:
                print(prepare_cli_text(message), file=sys.stderr)
            except Exception:
                print(message, file=sys.stderr)
        return 1
    except Exception as err:
        from namel3ss.cli.text_output import prepare_cli_text
        from namel3ss.errors.contract import build_error_entry

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
