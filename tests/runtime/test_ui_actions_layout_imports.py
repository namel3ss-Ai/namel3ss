import ast
from pathlib import Path

from namel3ss.runtime.ui.actions import handle_action
from namel3ss.runtime.ui.actions.build.action_registry import ACTION_HANDLERS
from namel3ss.runtime.ui.actions.build.build import handle_action as dispatch_handle_action
from namel3ss.runtime.ui.actions.build.dispatch_context import ActionDispatchContext
from namel3ss.runtime.ui.actions.chat.branch_selector import handle_chat_branch_select_action
from namel3ss.runtime.ui.actions.chat.flow_action import handle_call_flow_action
from namel3ss.runtime.ui.actions.chat.form_submit import handle_submit_form_action
from namel3ss.runtime.ui.actions.chat.message_regenerator import handle_chat_message_regenerate_action
from namel3ss.runtime.ui.actions.chat.message_sender import handle_chat_message_send_action
from namel3ss.runtime.ui.actions.chat.model_selector import handle_chat_model_select_action
from namel3ss.runtime.ui.actions.chat.stream_cancel import handle_chat_stream_cancel_action
from namel3ss.runtime.ui.actions.chat.thread_creator import handle_chat_thread_new_action
from namel3ss.runtime.ui.actions.chat.thread_selector import handle_chat_thread_select_action
from namel3ss.runtime.ui.actions.ingestion.review import handle_ingestion_review_action
from namel3ss.runtime.ui.actions.ingestion.run import handle_ingestion_run_action
from namel3ss.runtime.ui.actions.ingestion.skip import handle_ingestion_skip_action
from namel3ss.runtime.ui.actions.retrieval.run import handle_retrieval_run_action
from namel3ss.runtime.ui.actions.settings.theme_update import handle_theme_settings_update_action
from namel3ss.runtime.ui.actions.upload.clear import handle_upload_clear_action
from namel3ss.runtime.ui.actions.upload.replace import handle_upload_replace_action
from namel3ss.runtime.ui.actions.upload.select import handle_upload_select_action
from namel3ss.runtime.ui.state.scope_select import handle_scope_select_action


def test_ui_action_import_paths_are_stable() -> None:
    assert handle_action is dispatch_handle_action
    assert isinstance(ActionDispatchContext, type)
    assert callable(handle_call_flow_action)
    assert callable(handle_submit_form_action)
    assert callable(handle_chat_branch_select_action)
    assert callable(handle_chat_message_regenerate_action)
    assert callable(handle_chat_message_send_action)
    assert callable(handle_chat_model_select_action)
    assert callable(handle_chat_stream_cancel_action)
    assert callable(handle_chat_thread_new_action)
    assert callable(handle_chat_thread_select_action)
    assert callable(handle_ingestion_review_action)
    assert callable(handle_ingestion_run_action)
    assert callable(handle_ingestion_skip_action)
    assert callable(handle_retrieval_run_action)
    assert callable(handle_upload_select_action)
    assert callable(handle_upload_clear_action)
    assert callable(handle_upload_replace_action)
    assert callable(handle_theme_settings_update_action)
    assert callable(handle_scope_select_action)


def test_ui_action_registry_is_explicit_and_stable() -> None:
    assert sorted(ACTION_HANDLERS.keys()) == [
        "call_flow",
        "chat.branch.select",
        "chat.message.regenerate",
        "chat.message.send",
        "chat.model.select",
        "chat.stream.cancel",
        "chat.thread.new",
        "chat.thread.select",
        "chat_model_select",
        "chat_thread_select",
        "ingestion_review",
        "ingestion_run",
        "ingestion_skip",
        "retrieval_run",
        "scope_select",
        "submit_form",
        "theme_settings_update",
        "upload_clear",
        "upload_replace",
        "upload_select",
    ]
    assert all(callable(handler) for handler in ACTION_HANDLERS.values())


def test_ui_action_package_has_domain_first_layout() -> None:
    actions_root = Path("src/namel3ss/runtime/ui/actions")
    action_files = sorted(
        path.name for path in actions_root.iterdir() if path.is_file() and path.suffix == ".py"
    )
    action_dirs = sorted(
        path.name for path in actions_root.iterdir() if path.is_dir() and path.name != "__pycache__"
    )
    assert action_files == ["__init__.py"]
    assert action_dirs == ["build", "chat", "ingestion", "retrieval", "settings", "upload", "validation"]

    state_root = Path("src/namel3ss/runtime/ui/state")
    state_files = sorted(path.name for path in state_root.iterdir() if path.is_file() and path.suffix == ".py")
    assert state_files == [
        "__init__.py",
        "chat_shell.py",
        "dispatch.py",
        "form_policy.py",
        "model.py",
        "pdf_preview_state.py",
        "permissions.py",
        "scope_select.py",
        "state_target.py",
    ]

    assert Path("src/namel3ss/runtime/ui/actions/build/action_registry.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/build/dispatch_context.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/build/dispatch_contract.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/chat/dispatch.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/ingestion/dispatch.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/retrieval/dispatch.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/settings/dispatch.py").is_file()
    assert Path("src/namel3ss/runtime/ui/actions/upload/dispatch.py").is_file()
    assert Path("src/namel3ss/runtime/ui/state/dispatch.py").is_file()


def test_ui_runtime_files_remain_under_500_loc() -> None:
    root = Path("src/namel3ss/runtime/ui")
    for path in sorted(root.rglob("*.py")):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 450, f"{path.as_posix()} exceeds 450 LOC with {line_count} lines"


def test_runtime_ui_import_boundaries_are_enforced() -> None:
    root = Path("src/namel3ss/runtime/ui")
    disallowed_imports = (
        "namel3ss.ast",
        "namel3ss.ir",
        "namel3ss.parser",
        "namel3ss.studio",
    )
    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        imported_modules: set[str] = set()
        parsed = ast.parse(source)
        for node in ast.walk(parsed):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name)
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)
        for imported in imported_modules:
            for token in disallowed_imports:
                assert not (imported == token or imported.startswith(f"{token}.")), (
                    f"{path.as_posix()} imports disallowed module '{imported}'"
                )
