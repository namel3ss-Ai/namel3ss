from __future__ import annotations

import os
import sys

from namel3ss.cli.aliases import canonical_command
from namel3ss.cli.app_handler import handle_app_commands
from namel3ss.cli.auth_mode import run_auth_command
from namel3ss.cli.artifacts_mode import run_artifacts_clean, run_artifacts_status
from namel3ss.cli.audit_mode import run_audit_command
from namel3ss.cli.ast_mode import run_ast_command
from namel3ss.cli.browser_mode import run_dev_command, run_preview_command
from namel3ss.cli.build_mode import run_build_command
from namel3ss.cli.create_mode import run_create_command
from namel3ss.cli.dataset_mode import run_dataset_command
from namel3ss.cli.constants import ROOT_APP_COMMANDS
from namel3ss.cli.deps_mode import run_deps
from namel3ss.cli.dependency_management_mode import run_dependency_root
from namel3ss.cli.discover_mode import run_discover
from namel3ss.cli.doctor import run_doctor
from namel3ss.cli.editor_mode import run_editor_command
from namel3ss.cli.eval_mode import run_eval_command
from namel3ss.cli.export_mode import run_export_command
from namel3ss.cli.exists_mode import run_exists_command
from namel3ss.cli.explain_mode import run_explain_command
from namel3ss.cli.conventions_mode import run_conventions_command
from namel3ss.cli.concurrency_mode import run_concurrency_command
from namel3ss.cli.compile_mode import run_compile_command
from namel3ss.cli.debug_mode import run_debug_command
from namel3ss.cli.feedback_mode import run_feedback_command
from namel3ss.cli.docs_mode import run_docs_command
from namel3ss.cli.init_mode import run_init_command
from namel3ss.cli.expr_check_mode import run_expr_check_command
from namel3ss.cli.first_run import is_first_run
from namel3ss.cli.fix_mode import run_fix_command
from namel3ss.cli.how_mode import run_how_command
from namel3ss.cli.kit_mode import run_kit_command
from namel3ss.cli.memory_mode import run_memory_command
from namel3ss.cli.migrate_mode import run_migrate_command
from namel3ss.cli.metrics_mode import run_metrics_command
from namel3ss.cli.observe_mode import run_observe_command
from namel3ss.cli.formats_mode import run_formats_command
from namel3ss.cli.plugin_mode import run_plugin_command
from namel3ss.cli.package_mode import run_package_command
from namel3ss.cli.playground_mode import run_playground_command
from namel3ss.cli.prompts_mode import run_prompts_command
from namel3ss.cli.retrain_mode import run_retrain_command
from namel3ss.cli.quality_mode import run_quality_command
from namel3ss.cli.sandbox_mode import run_sandbox_command
from namel3ss.cli.sensitive_mode import run_sensitive_command
from namel3ss.cli.packs_mode import run_packs
from namel3ss.cli.pattern_mode import run_pattern
from namel3ss.cli.persist_mode import run_data, run_persist
from namel3ss.cli.pkg_mode import run_pkg
from namel3ss.cli.sdk_mode import run_sdk_command
from namel3ss.cli.promote_mode import run_promote_command
from namel3ss.cli.proof_mode import run_proof_command
from namel3ss.cli.readability_mode import run_readability_command
from namel3ss.cli.replay_mode import run_replay_command
from namel3ss.cli.registry_mode import run_registry
from namel3ss.cli.reserved_mode import run_reserved_command
from namel3ss.cli.secret_mode import run_secret_command
from namel3ss.cli.icons_mode import run_icons_command
from namel3ss.cli.policy_mode import run_policy_command
from namel3ss.cli.release_check_mode import run_release_check_command
from namel3ss.cli.run_entry import dispatch_run_command
from namel3ss.cli.scaffold_mode import run_new
from namel3ss.cli.secrets_mode import run_secrets_command
from namel3ss.cli.serve_mode import run_serve_command
from namel3ss.cli.session_mode import run_session_command
from namel3ss.cli.start_mode import run_start_command
from namel3ss.cli.studio_connect_mode import run_studio_connect_command
from namel3ss.cli.tutorial_mode import run_tutorial_command
from namel3ss.cli.schema_mode import run_schema_command
from namel3ss.cli.model_mode import run_model_command
from namel3ss.cli.models_mode import run_models_command
from namel3ss.cli.security_mode import run_security_command
from namel3ss.cli.tenant_mode import run_tenant_command
from namel3ss.cli.federation_mode import run_federation_command
from namel3ss.cli.cluster_mode import run_cluster_command
from namel3ss.cli.observability_mode import run_observability_command
from namel3ss.cli.trace_mode import run_trace_command
from namel3ss.cli.trigger_mode import run_trigger_command
from namel3ss.cli.type_mode import run_type_command
from namel3ss.cli.version_mode import run_version_command
from namel3ss.cli.wasm_mode import run_wasm_command
from namel3ss.cli.mlops_mode import run_mlops_command
from namel3ss.cli.lsp_mode import run_lsp_command
from namel3ss.cli.see_mode import run_see_command
from namel3ss.cli.scaffold_tool_mode import run_scaffold_command
from namel3ss.cli.status_mode import run_status_command
from namel3ss.cli.test_mode import run_test_command
from namel3ss.cli.train_mode import run_train_command
from namel3ss.cli.text_output import prepare_cli_text, prepare_first_run_text
from namel3ss.cli.template_shortcuts import (
    TEMPLATE_LIST_COMMAND,
    find_template_shortcut,
    render_template_list,
    render_template_shortcut,
)
from namel3ss.cli.tools_mode import run_tools
from namel3ss.cli.ui_output import print_usage, print_version
from namel3ss.cli.verify_mode import run_verify_command
from namel3ss.cli.what_mode import run_what_command
from namel3ss.cli.when_mode import run_when_command
from namel3ss.cli.why_mode import run_why_command
from namel3ss.cli.with_mode import run_with_command
from namel3ss.cli.marketplace_mode import run_marketplace_command
from namel3ss.cli.manifest_mode import run_manifest_command
from namel3ss.cli.plugin_registry_mode import run_plugin_registry_command
from namel3ss.cli.validate_mode import run_validate_command
from namel3ss.errors.base import Namel3ssError
from namel3ss.errors.contract import build_error_entry
from namel3ss.errors.render import format_error, format_first_run_error

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
        if cmd == TEMPLATE_LIST_COMMAND:
            if args[1:] and canonical_command(args[1]) == "plugins":
                return run_plugin_registry_command(["list", "plugins", *args[2:]])
            if args[1:]:
                raise Namel3ssError(f"Usage: n3 {TEMPLATE_LIST_COMMAND}")
            print(render_template_list())
            return 0
        shortcut = find_template_shortcut(cmd)
        if shortcut is not None:
            if args[1:]:
                raise Namel3ssError(f"Usage: n3 {shortcut.command}")
            print(render_template_shortcut(shortcut))
            return 0
        if cmd == "reserved":
            return run_reserved_command(args[1:])
        if cmd == "icons":
            return run_icons_command(args[1:])
        if cmd == "status":
            tail = args[1:]
            if tail:
                return run_status_command(tail)
            return run_artifacts_status(tail)
        if cmd == "clean":
            return run_artifacts_clean(args[1:])
        if cmd == "doctor":
            return run_doctor(args[1:])
        if cmd == "doc":
            from namel3ss.cli.doc_mode import run_doc_command

            return run_doc_command(args[1:])
        if cmd == "docs":
            return run_docs_command(args[1:])
        if cmd == "init":
            return run_init_command(args[1:])
        if cmd == "version":
            if len(args) > 1:
                return run_version_command(args[1:])
            print_version()
            return 0
        if cmd == "help":
            print_usage()
            return 0
        if cmd == "run":
            return dispatch_run_command(args[1:])
        if cmd == "serve":
            return run_serve_command(args[1:])
        if cmd == "session":
            return run_session_command(args[1:])
        if cmd == "studio" and args[1:] and canonical_command(args[1]) == "connect":
            return run_studio_connect_command(args[2:])
        if cmd == "manifest":
            return run_manifest_command(args[1:])
        if cmd == "validate":
            return run_validate_command(args[1:])
        if cmd == "create":
            return run_create_command(args[1:])
        if cmd == "publish" and args[1:] and canonical_command(args[1]) == "plugin":
            return run_plugin_registry_command(["publish", "plugin", *args[2:]])
        if cmd == "install" and args[1:] and canonical_command(args[1]) == "plugin":
            return run_plugin_registry_command(["install", "plugin", *args[2:]])
        if cmd in {"install", "update", "tree"}:
            return run_dependency_root(cmd, args[1:])
        if cmd == "dev":
            return run_dev_command(args[1:])
        if cmd == "preview":
            return run_preview_command(args[1:])
        if cmd == "start":
            return run_start_command(args[1:])
        if cmd == "pack":
            if args[1:]:
                next_token = canonical_command(args[1])
                if next_token in PACK_SUBCOMMANDS:
                    return run_packs(args[1:])
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
        if cmd == "export":
            return run_export_command(args[1:])
        if cmd == "secrets":
            return run_secrets_command(args[1:])
        if cmd == "observe":
            return run_observe_command(args[1:])
        if cmd == "trace":
            return run_trace_command(args[1:])
        if cmd == "replay":
            return run_replay_command(args[1:])
        if cmd == "debug":
            return run_debug_command(args[1:])
        if cmd == "observability":
            return run_observability_command(args[1:])
        if cmd == "metrics":
            return run_metrics_command(args[1:])
        if cmd == "ast":
            return run_ast_command(args[1:])
        if cmd == "type":
            return run_type_command(args[1:])
        if cmd == "schema":
            return run_schema_command(args[1:])
        if cmd == "concurrency":
            return run_concurrency_command(args[1:])
        if cmd == "compile":
            return run_compile_command(args[1:])
        if cmd == "trigger":
            return run_trigger_command(args[1:])
        if cmd == "conventions":
            return run_conventions_command(args[1:])
        if cmd == "formats":
            return run_formats_command(args[1:])
        if cmd == "audit":
            return run_audit_command(args[1:])
        if cmd == "auth":
            return run_auth_command(args[1:])
        if cmd == "secret":
            return run_secret_command(args[1:])
        if cmd == "security":
            return run_security_command(args[1:])
        if cmd == "policy":
            return run_policy_command(args[1:])
        if cmd == "prompts":
            return run_prompts_command(args[1:])
        if cmd == "feedback":
            return run_feedback_command(args[1:])
        if cmd == "dataset":
            return run_dataset_command(args[1:])
        if cmd == "train":
            return run_train_command(args[1:])
        if cmd == "retrain":
            return run_retrain_command(args[1:])
        if cmd == "model":
            return run_model_command(args[1:])
        if cmd == "models":
            return run_models_command(args[1:])
        if cmd == "tenant":
            return run_tenant_command(args[1:])
        if cmd == "federation":
            return run_federation_command(args[1:])
        if cmd == "cluster":
            return run_cluster_command(args[1:])
        if cmd == "marketplace":
            return run_marketplace_command(args[1:])
        if cmd == "wasm":
            return run_wasm_command(args[1:])
        if cmd == "quality":
            return run_quality_command(args[1:])
        if cmd == "mlops":
            return run_mlops_command(args[1:])
        if cmd == "tutorial":
            return run_tutorial_command(args[1:])
        if cmd == "playground":
            return run_playground_command(args[1:])
        if cmd == "scaffold":
            return run_scaffold_command(args[1:])
        if cmd == "package":
            return run_package_command(args[1:])
        if cmd == "lsp":
            return run_lsp_command(args[1:])
        if cmd == "sensitive":
            return run_sensitive_command(args[1:])
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
        if cmd == "sandbox":
            return run_sandbox_command(args[1:])
        if cmd == "plugin":
            return run_plugin_command(args[1:])
        if cmd == "packs":
            return run_packs(args[1:])
        if cmd == "sdk":
            return run_sdk_command(args[1:])
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
        if cmd in ROOT_APP_COMMANDS:
            return handle_app_commands(None, [cmd, *args[1:]], context)

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
