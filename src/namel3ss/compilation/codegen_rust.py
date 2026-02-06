from __future__ import annotations

import sys
from pathlib import Path

from namel3ss.compilation.model import (
    BinaryNumber,
    GeneratedProject,
    InputNumber,
    LocalNumber,
    NumberLiteral,
    NumericExpr,
    NumericFlowPlan,
    UnaryNumber,
)


RUST_EDITION = "2021"


def generate_rust_project(plan: NumericFlowPlan, out_root: Path, *, wasm: bool) -> GeneratedProject:
    flow_slug = _slug(plan.flow_name)
    root = out_root / plan.flow_name / ("wasm" if wasm else "rust")
    cargo_toml = root / "Cargo.toml"
    lib_rs = root / "src" / "lib.rs"
    header_rs = root / "namel3ss.rs"
    readme = root / "README.md"

    files: dict[Path, str] = {
        cargo_toml: _render_cargo_toml(flow_slug, wasm=wasm),
        lib_rs: _render_lib_rs(plan),
        header_rs: _render_wrapper_rs(),
        readme: _render_readme(flow_slug, wasm=wasm),
    }
    if wasm:
        files[root / "src" / "main.rs"] = _render_main_rs(flow_slug)
    else:
        files[root / "examples" / "go" / "main.go"] = _render_go_example()
        files[root / "examples" / "node" / "index.js"] = _render_node_example()

    _write_files(files)

    artifact_path, build_cmd = _artifact_and_command(flow_slug, wasm=wasm)
    return GeneratedProject(
        flow_name=plan.flow_name,
        language="wasm" if wasm else "rust",
        root=root,
        artifact=root / artifact_path,
        header=header_rs,
        files=tuple(sorted(files.keys(), key=lambda item: item.as_posix())),
        build_command=tuple(build_cmd),
    )


def _artifact_and_command(flow_slug: str, *, wasm: bool) -> tuple[Path, list[str]]:
    if wasm:
        artifact = Path("target") / "wasm32-wasip1" / "release" / "flow_runner.wasm"
        cmd = ["cargo", "build", "--release", "--target", "wasm32-wasip1"]
        return artifact, cmd
    if sys.platform.startswith("win"):
        artifact = Path("target") / "release" / f"{flow_slug}.dll"
    elif sys.platform == "darwin":
        artifact = Path("target") / "release" / f"lib{flow_slug}.dylib"
    else:
        artifact = Path("target") / "release" / f"lib{flow_slug}.so"
    cmd = ["cargo", "build", "--release"]
    return artifact, cmd


def _render_cargo_toml(flow_slug: str, *, wasm: bool) -> str:
    package_name = f"namel3ss_{flow_slug}"
    lines = [
        "[package]",
        f'name = "{package_name}"',
        'version = "0.0.0"',
        f'edition = "{RUST_EDITION}"',
        "",
        "[lib]",
        f'name = "{flow_slug}"',
        'crate-type = ["cdylib"]',
        "",
        "[dependencies]",
    ]
    if wasm:
        lines.extend(
            [
                "",
                "[[bin]]",
                'name = "flow_runner"',
                'path = "src/main.rs"',
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _render_lib_rs(plan: NumericFlowPlan) -> str:
    assignments = "\n".join(
        [f"    let local_{_var_name(item.name)}: f64 = {_emit_expr(item.expr)};" for item in plan.assignments]
    )
    input_extracts = "\n".join(
        [
            f"    let input_{_var_name(key)} = extract_number(input_json, \"{_escape_rust(key)}\")"
            f".ok_or_else(|| String::from(\"missing_or_invalid_input_{_escape_rust(key)}\"))?;"
            for key in plan.input_keys
        ]
    )
    result_expr = _emit_expr(plan.result)

    return (
        "use std::ffi::{CStr, CString};\n"
        "use std::os::raw::c_char;\n"
        "\n"
        "pub fn run_flow_json(input_json: &str) -> Result<String, String> {\n"
        f"{input_extracts}\n"
        f"{assignments}\n"
        f"    let result: f64 = {result_expr};\n"
        "    if !result.is_finite() {\n"
        "        return Err(String::from(\"result_not_finite\"));\n"
        "    }\n"
        "    Ok(format!(\"{\\\"result\\\":{}}\", format_number(result)))\n"
        "}\n"
        "\n"
        "fn format_number(value: f64) -> String {\n"
        "    let mut text = format!(\"{:.17}\", value);\n"
        "    while text.contains('.') && text.ends_with('0') {\n"
        "        text.pop();\n"
        "    }\n"
        "    if text.ends_with('.') {\n"
        "        text.pop();\n"
        "    }\n"
        "    if text == \"-0\" {\n"
        "        return String::from(\"0\");\n"
        "    }\n"
        "    text\n"
        "}\n"
        "\n"
        "fn extract_number(json: &str, key: &str) -> Option<f64> {\n"
        "    let key_token = format!(\"\\\"{}\\\"\", key);\n"
        "    let key_pos = json.find(&key_token)?;\n"
        "    let after_key = &json[key_pos + key_token.len()..];\n"
        "    let colon_pos = after_key.find(':')?;\n"
        "    let mut cursor = &after_key[colon_pos + 1..];\n"
        "    cursor = cursor.trim_start();\n"
        "    let mut end = 0usize;\n"
        "    for (idx, ch) in cursor.char_indices() {\n"
        "        if ch.is_ascii_digit() || ch == '.' || ch == '-' || ch == '+' || ch == 'e' || ch == 'E' {\n"
        "            end = idx + ch.len_utf8();\n"
        "            continue;\n"
        "        }\n"
        "        break;\n"
        "    }\n"
        "    if end == 0 {\n"
        "        return None;\n"
        "    }\n"
        "    let number_text = &cursor[..end];\n"
        "    number_text.parse::<f64>().ok()\n"
        "}\n"
        "\n"
        "#[no_mangle]\n"
        "pub extern \"C\" fn run_flow(\n"
        "    input_json: *const c_char,\n"
        "    output_json: *mut *mut c_char,\n"
        "    error_json: *mut *mut c_char,\n"
        ") -> i32 {\n"
        "    if output_json.is_null() || error_json.is_null() {\n"
        "        return 1;\n"
        "    }\n"
        "    unsafe {\n"
        "        *output_json = std::ptr::null_mut();\n"
        "        *error_json = std::ptr::null_mut();\n"
        "    }\n"
        "\n"
        "    let input_text = if input_json.is_null() {\n"
        "        String::from(\"{}\")\n"
        "    } else {\n"
        "        let cstr = unsafe { CStr::from_ptr(input_json) };\n"
        "        match cstr.to_str() {\n"
        "            Ok(value) => value.to_string(),\n"
        "            Err(_) => {\n"
        "                set_error(error_json, \"invalid_utf8_input\");\n"
        "                return 1;\n"
        "            }\n"
        "        }\n"
        "    };\n"
        "\n"
        "    match run_flow_json(&input_text) {\n"
        "        Ok(payload) => {\n"
        "            let c = match CString::new(payload) {\n"
        "                Ok(value) => value,\n"
        "                Err(_) => {\n"
        "                    set_error(error_json, \"output_contains_nul\");\n"
        "                    return 1;\n"
        "                }\n"
        "            };\n"
        "            unsafe { *output_json = c.into_raw(); }\n"
        "            0\n"
        "        }\n"
        "        Err(message) => {\n"
        "            set_error(error_json, &message);\n"
        "            1\n"
        "        }\n"
        "    }\n"
        "}\n"
        "\n"
        "fn set_error(error_json: *mut *mut c_char, message: &str) {\n"
        "    let payload = format!(\"{{\\\"error\\\":\\\"{}\\\"}}\", message);\n"
        "    if let Ok(c) = CString::new(payload) {\n"
        "        unsafe { *error_json = c.into_raw(); }\n"
        "    }\n"
        "}\n"
        "\n"
        "#[no_mangle]\n"
        "pub extern \"C\" fn free_json_string(ptr: *mut c_char) {\n"
        "    if ptr.is_null() {\n"
        "        return;\n"
        "    }\n"
        "    unsafe {\n"
        "        let _ = CString::from_raw(ptr);\n"
        "    }\n"
        "}\n"
    )


def _render_main_rs(flow_slug: str) -> str:
    return (
        "fn main() {\n"
        "    let input = std::env::args().nth(1).unwrap_or_else(|| String::from(\"{}\"));\n"
        f"    match {flow_slug}::run_flow_json(&input) {{\n"
        "        Ok(output) => {\n"
        "            println!(\"{}\", output);\n"
        "        }\n"
        "        Err(err) => {\n"
        "            eprintln!(\"{}\", err);\n"
        "            std::process::exit(1);\n"
        "        }\n"
        "    }\n"
        "}\n"
    )


def _render_wrapper_rs() -> str:
    return (
        "use std::ffi::{CStr, CString};\n"
        "use std::os::raw::c_char;\n"
        "\n"
        "extern \"C\" {\n"
        "    fn run_flow(input_json: *const c_char, output_json: *mut *mut c_char, error_json: *mut *mut c_char) -> i32;\n"
        "    fn free_json_string(ptr: *mut c_char);\n"
        "}\n"
        "\n"
        "pub fn call_run_flow(input: &str) -> Result<String, String> {\n"
        "    let input_c = CString::new(input).map_err(|_| String::from(\"input_contains_nul\"))?;\n"
        "    let mut out_ptr: *mut c_char = std::ptr::null_mut();\n"
        "    let mut err_ptr: *mut c_char = std::ptr::null_mut();\n"
        "    let status = unsafe { run_flow(input_c.as_ptr(), &mut out_ptr, &mut err_ptr) };\n"
        "    if status == 0 {\n"
        "        if out_ptr.is_null() {\n"
        "            return Err(String::from(\"missing_output\"));\n"
        "        }\n"
        "        let text = unsafe { CStr::from_ptr(out_ptr) }.to_string_lossy().into_owned();\n"
        "        unsafe { free_json_string(out_ptr); }\n"
        "        return Ok(text);\n"
        "    }\n"
        "    if err_ptr.is_null() {\n"
        "        return Err(String::from(\"unknown_error\"));\n"
        "    }\n"
        "    let text = unsafe { CStr::from_ptr(err_ptr) }.to_string_lossy().into_owned();\n"
        "    unsafe { free_json_string(err_ptr); }\n"
        "    Err(text)\n"
        "}\n"
    )


def _render_go_example() -> str:
    return (
        "package main\n"
        "\n"
        "/*\n"
        "#cgo LDFLAGS: -lnamel3ss_compiled\n"
        "#include <stdlib.h>\n"
        "int run_flow(const char *input_json, char **output_json, char **error_json);\n"
        "void free_json_string(char *ptr);\n"
        "*/\n"
        "import \"C\"\n"
        "\n"
        "import (\n"
        "\t\"fmt\"\n"
        "\t\"unsafe\"\n"
        ")\n"
        "\n"
        "func main() {\n"
        "\tinput := C.CString(`{\"a\":2,\"b\":3}`)\n"
        "\tdefer C.free(unsafe.Pointer(input))\n"
        "\tvar out *C.char\n"
        "\tvar err *C.char\n"
        "\tstatus := C.run_flow(input, &out, &err)\n"
        "\tif status != 0 {\n"
        "\t\tfmt.Println(C.GoString(err))\n"
        "\t\tC.free_json_string(err)\n"
        "\t\treturn\n"
        "\t}\n"
        "\tfmt.Println(C.GoString(out))\n"
        "\tC.free_json_string(out)\n"
        "}\n"
    )


def _render_node_example() -> str:
    return (
        "const ffi = require('ffi-napi');\n"
        "const ref = require('ref-napi');\n"
        "\n"
        "const charPtr = ref.refType('char');\n"
        "const charPtrPtr = ref.refType(charPtr);\n"
        "\n"
        "const lib = ffi.Library('./libflow', {\n"
        "  run_flow: ['int', ['string', charPtrPtr, charPtrPtr]],\n"
        "  free_json_string: ['void', [charPtr]],\n"
        "});\n"
        "\n"
        "const out = ref.alloc(charPtr);\n"
        "const err = ref.alloc(charPtr);\n"
        "const status = lib.run_flow('{\"a\":2,\"b\":3}', out, err);\n"
        "if (status !== 0) {\n"
        "  const msg = ref.readCString(err.deref(), 0);\n"
        "  lib.free_json_string(err.deref());\n"
        "  throw new Error(msg);\n"
        "}\n"
        "const payload = ref.readCString(out.deref(), 0);\n"
        "lib.free_json_string(out.deref());\n"
        "console.log(payload);\n"
    )


def _render_readme(flow_slug: str, *, wasm: bool) -> str:
    language = "wasm" if wasm else "rust"
    build = "cargo build --release --target wasm32-wasip1" if wasm else "cargo build --release"
    return (
        f"# Compiled Flow {flow_slug} ({language})\n"
        "\n"
        "Exports:\n"
        "\n"
        "- `run_flow`\n"
        "- `free_json_string`\n"
        "\n"
        "Build with:\n"
        "\n"
        "```bash\n"
        f"{build}\n"
        "```\n"
    )


def _emit_expr(expr: NumericExpr) -> str:
    if isinstance(expr, NumberLiteral):
        return f"{expr.text}f64"
    if isinstance(expr, InputNumber):
        return f"input_{_var_name(expr.key)}"
    if isinstance(expr, LocalNumber):
        return f"local_{_var_name(expr.name)}"
    if isinstance(expr, UnaryNumber):
        return f"({expr.op}{_emit_expr(expr.operand)})"
    if isinstance(expr, BinaryNumber):
        return f"({_emit_expr(expr.left)} {expr.op} {_emit_expr(expr.right)})"
    raise ValueError(f"Unsupported numeric expr: {expr}")


def _write_files(files: dict[Path, str]) -> None:
    for path in sorted(files.keys(), key=lambda item: item.as_posix()):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[path], encoding="utf-8")


def _slug(name: str) -> str:
    chars = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            chars.append(ch.lower())
        else:
            chars.append("_")
    text = "".join(chars).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    if not text:
        text = "flow"
    if text[0].isdigit():
        text = f"flow_{text}"
    return text


def _var_name(name: str) -> str:
    return _slug(name)


def _escape_rust(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


__all__ = ["generate_rust_project"]
