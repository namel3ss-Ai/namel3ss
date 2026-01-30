use std::collections::BTreeMap;

use crate::json::push_json_string;
use crate::json_parse::{parse_json, JsonValue};
use crate::n3_status;

pub fn execute_ir(ir_json: &str, config_json: Option<&str>) -> Result<Vec<u8>, n3_status> {
    let root = parse_json(ir_json).map_err(|_| n3_status::N3_STATUS_INVALID_ARGUMENT)?;
    let config = match config_json {
        Some(text) if !text.trim().is_empty() => Some(parse_json(text).map_err(|_| n3_status::N3_STATUS_INVALID_ARGUMENT)?),
        _ => None,
    };
    let flow_name = config
        .as_ref()
        .and_then(|value| object_field(value, "flow_name"))
        .and_then(value_as_string)
        .map(|s| s.to_string());
    let runtime_theme = config
        .as_ref()
        .and_then(|value| object_field(value, "runtime_theme"))
        .cloned()
        .unwrap_or(JsonValue::Null);
    let theme_source = config
        .as_ref()
        .and_then(|value| object_field(value, "theme_source"))
        .cloned()
        .unwrap_or(JsonValue::Null);

    let flows = object_field(&root, "flows")
        .and_then(value_as_array)
        .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
    let flow = select_flow(flows, flow_name.as_deref())?;
    let flow_name = object_field(flow, "name")
        .and_then(value_as_string)
        .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
    let flow_line = object_field(flow, "line").and_then(value_as_i64);
    let flow_column = object_field(flow, "column").and_then(value_as_i64);
    let body = object_field(flow, "body")
        .and_then(value_as_array)
        .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;

    let mut state: BTreeMap<String, JsonValue> = BTreeMap::new();
    let mut steps: Vec<JsonValue> = Vec::new();
    let mut counter: u32 = 0;
    record_step(
        &mut steps,
        &mut counter,
        "flow_start",
        &format!("flow \"{}\" started", flow_name),
        None,
        flow_line,
        flow_column,
    );
    let mut last_value = JsonValue::Null;
    for stmt in body {
        let stmt_type = object_field(stmt, "type")
            .and_then(value_as_string)
            .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
        match stmt_type {
            "Set" => {
                let target = object_field(stmt, "target")
                    .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
                let target_path = state_path(target)?;
                let expr = object_field(stmt, "expression")
                    .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
                let value = eval_expr(expr, &state)?;
                set_state_path(&mut state, &target_path, value.clone())?;
                let line = object_field(stmt, "line").and_then(value_as_i64);
                let column = object_field(stmt, "column").and_then(value_as_i64);
                record_step(
                    &mut steps,
                    &mut counter,
                    "statement_set",
                    &format!("set state.{}", target_path.join(".")),
                    None,
                    line,
                    column,
                );
                last_value = value;
            }
            "Return" => {
                let expr = object_field(stmt, "expression")
                    .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
                last_value = eval_expr(expr, &state)?;
                let line = object_field(stmt, "line").and_then(value_as_i64);
                let column = object_field(stmt, "column").and_then(value_as_i64);
                record_step(
                    &mut steps,
                    &mut counter,
                    "statement_return",
                    "returned a value",
                    None,
                    line,
                    column,
                );
                break;
            }
            _ => return Err(n3_status::N3_STATUS_NOT_IMPLEMENTED),
        }
    }
    record_step(
        &mut steps,
        &mut counter,
        "flow_end",
        &format!("flow \"{}\" ended", flow_name),
        Some("completed successfully"),
        flow_line,
        flow_column,
    );

    let mut output = BTreeMap::new();
    output.insert("execution_steps".to_string(), JsonValue::Array(steps));
    output.insert("last_value".to_string(), last_value);
    output.insert("runtime_theme".to_string(), runtime_theme);
    output.insert("state".to_string(), JsonValue::Object(state));
    output.insert("theme_source".to_string(), theme_source);
    output.insert("traces".to_string(), JsonValue::Array(Vec::new()));

    let json = json_string(&JsonValue::Object(output));
    Ok(json.into_bytes())
}

fn record_step(
    steps: &mut Vec<JsonValue>,
    counter: &mut u32,
    kind: &str,
    what: &str,
    because: Option<&str>,
    line: Option<i64>,
    column: Option<i64>,
) {
    *counter += 1;
    let mut map = BTreeMap::new();
    map.insert("because".to_string(), match because {
        Some(value) => JsonValue::String(value.to_string()),
        None => JsonValue::Null,
    });
    map.insert("column".to_string(), line_column_value(column));
    map.insert("data".to_string(), JsonValue::Object(BTreeMap::new()));
    map.insert("id".to_string(), JsonValue::String(format!("step:{:04}", counter)));
    map.insert("kind".to_string(), JsonValue::String(kind.to_string()));
    map.insert("line".to_string(), line_column_value(line));
    map.insert("what".to_string(), JsonValue::String(what.to_string()));
    steps.push(JsonValue::Object(map));
}

fn line_column_value(value: Option<i64>) -> JsonValue {
    match value {
        Some(num) => JsonValue::Number(num),
        None => JsonValue::Null,
    }
}

fn eval_expr(expr: &JsonValue, state: &BTreeMap<String, JsonValue>) -> Result<JsonValue, n3_status> {
    let expr_type = object_field(expr, "type")
        .and_then(value_as_string)
        .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
    match expr_type {
        "Literal" => {
            let value = object_field(expr, "value").ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
            Ok(value.clone())
        }
        "StatePath" => {
            let path = state_path(expr)?;
            resolve_state_path(state, &path)
        }
        _ => Err(n3_status::N3_STATUS_NOT_IMPLEMENTED),
    }
}

fn state_path(value: &JsonValue) -> Result<Vec<String>, n3_status> {
    let kind = object_field(value, "type")
        .and_then(value_as_string)
        .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
    if kind != "StatePath" {
        return Err(n3_status::N3_STATUS_NOT_IMPLEMENTED);
    }
    let path = object_field(value, "path")
        .and_then(value_as_array)
        .ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
    let mut segments = Vec::new();
    for item in path {
        let segment = value_as_string(item).ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)?;
        segments.push(segment.to_string());
    }
    Ok(segments)
}

fn resolve_state_path(state: &BTreeMap<String, JsonValue>, path: &[String]) -> Result<JsonValue, n3_status> {
    let mut current = JsonValue::Object(state.clone());
    for segment in path {
        match current {
            JsonValue::Object(map) => {
                if let Some(next) = map.get(segment) {
                    current = next.clone();
                } else {
                    return Err(n3_status::N3_STATUS_INVALID_ARGUMENT);
                }
            }
            _ => return Err(n3_status::N3_STATUS_INVALID_ARGUMENT),
        }
    }
    Ok(current)
}

fn set_state_path(
    state: &mut BTreeMap<String, JsonValue>,
    path: &[String],
    value: JsonValue,
) -> Result<(), n3_status> {
    if path.is_empty() {
        return Err(n3_status::N3_STATUS_INVALID_ARGUMENT);
    }
    if path.len() == 1 {
        state.insert(path[0].clone(), value);
        return Ok(());
    }
    let key = path[0].clone();
    let entry = state.entry(key).or_insert_with(|| JsonValue::Object(BTreeMap::new()));
    match entry {
        JsonValue::Object(map) => set_state_path(map, &path[1..], value),
        _ => {
            *entry = JsonValue::Object(BTreeMap::new());
            match entry {
                JsonValue::Object(map) => set_state_path(map, &path[1..], value),
                _ => Err(n3_status::N3_STATUS_INVALID_ARGUMENT),
            }
        }
    }
}

fn select_flow<'a>(flows: &'a [JsonValue], name: Option<&str>) -> Result<&'a JsonValue, n3_status> {
    if let Some(flow_name) = name {
        for flow in flows {
            if let Some(candidate) = object_field(flow, "name").and_then(value_as_string) {
                if candidate == flow_name {
                    return Ok(flow);
                }
            }
        }
        return Err(n3_status::N3_STATUS_INVALID_ARGUMENT);
    }
    flows.first().ok_or(n3_status::N3_STATUS_INVALID_ARGUMENT)
}

fn object_field<'a>(value: &'a JsonValue, key: &str) -> Option<&'a JsonValue> {
    match value {
        JsonValue::Object(map) => map.get(key),
        _ => None,
    }
}

fn value_as_string(value: &JsonValue) -> Option<&str> {
    match value {
        JsonValue::String(text) => Some(text.as_str()),
        _ => None,
    }
}

fn value_as_array(value: &JsonValue) -> Option<&[JsonValue]> {
    match value {
        JsonValue::Array(items) => Some(items.as_slice()),
        _ => None,
    }
}

fn value_as_i64(value: &JsonValue) -> Option<i64> {
    match value {
        JsonValue::Number(num) => Some(*num),
        _ => None,
    }
}

fn json_string(value: &JsonValue) -> String {
    let mut out = String::new();
    write_json_value(&mut out, value);
    out
}

fn write_json_value(out: &mut String, value: &JsonValue) {
    match value {
        JsonValue::Null => out.push_str("null"),
        JsonValue::Bool(value) => out.push_str(if *value { "true" } else { "false" }),
        JsonValue::Number(value) => out.push_str(&value.to_string()),
        JsonValue::String(value) => push_json_string(out, value),
        JsonValue::Array(items) => {
            out.push('[');
            for (idx, item) in items.iter().enumerate() {
                if idx > 0 {
                    out.push(',');
                }
                write_json_value(out, item);
            }
            out.push(']');
        }
        JsonValue::Object(map) => {
            out.push('{');
            for (idx, (key, value)) in map.iter().enumerate() {
                if idx > 0 {
                    out.push(',');
                }
                push_json_string(out, key);
                out.push(':');
                write_json_value(out, value);
            }
            out.push('}');
        }
    }
}
