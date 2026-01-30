#![allow(non_camel_case_types)]

use core::ptr;

mod chunk_plan;
mod exec;
mod json;
mod json_parse;
mod normalize;
mod scan;
mod sha256;

use chunk_plan::{plan_chunks, plan_to_json};
use exec::execute_ir;
use normalize::normalize_text;
use scan::{scan, tokens_to_json};
use sha256::hash_hex;

#[repr(C)]
#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum n3_status {
    N3_STATUS_OK = 0,
    N3_STATUS_NOT_IMPLEMENTED = 1,
    N3_STATUS_INVALID_ARGUMENT = 2,
    N3_STATUS_INVALID_STATE = 3,
    N3_STATUS_ERROR = 4,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct n3_buffer {
    pub data: *const u8,
    pub len: usize,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
pub struct n3_chunk_options {
    pub max_chars: u32,
    pub overlap: u32,
}

fn clear_buffer(out: *mut n3_buffer) {
    if out.is_null() {
        return;
    }
    unsafe {
        (*out).data = ptr::null();
        (*out).len = 0;
    }
}

fn set_buffer(out: *mut n3_buffer, data: Vec<u8>) {
    if out.is_null() {
        return;
    }
    if data.is_empty() {
        clear_buffer(out);
        return;
    }
    let boxed = data.into_boxed_slice();
    let len = boxed.len();
    let ptr = Box::into_raw(boxed) as *mut u8;
    unsafe {
        (*out).data = ptr as *const u8;
        (*out).len = len;
    }
}

fn buffer_as_slice<'a>(input: *const n3_buffer) -> Result<&'a [u8], n3_status> {
    if input.is_null() {
        return Err(n3_status::N3_STATUS_INVALID_ARGUMENT);
    }
    unsafe {
        let data = (*input).data;
        let len = (*input).len;
        if len == 0 {
            return Ok(&[]);
        }
        if data.is_null() {
            return Err(n3_status::N3_STATUS_INVALID_ARGUMENT);
        }
        Ok(std::slice::from_raw_parts(data, len))
    }
}

#[no_mangle]
pub extern "C" fn n3_native_info(out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    n3_status::N3_STATUS_NOT_IMPLEMENTED
}

#[no_mangle]
pub extern "C" fn n3_scan(source: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    let data = match buffer_as_slice(source) {
        Ok(value) => value,
        Err(status) => return status,
    };
    let text = match std::str::from_utf8(data) {
        Ok(value) => value,
        Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
    };
    let tokens = match scan(text) {
        Ok(result) => result,
        Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
    };
    let payload = tokens_to_json(&tokens);
    set_buffer(out, payload);
    n3_status::N3_STATUS_OK
}

#[no_mangle]
pub extern "C" fn n3_hash(source: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    let data = match buffer_as_slice(source) {
        Ok(value) => value,
        Err(status) => return status,
    };
    let digest = hash_hex(data);
    set_buffer(out, digest.into_bytes());
    n3_status::N3_STATUS_OK
}

#[no_mangle]
pub extern "C" fn n3_normalize(source: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    let data = match buffer_as_slice(source) {
        Ok(value) => value,
        Err(status) => return status,
    };
    let text = match std::str::from_utf8(data) {
        Ok(value) => value,
        Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
    };
    let normalized = normalize_text(text);
    set_buffer(out, normalized.into_bytes());
    n3_status::N3_STATUS_OK
}

#[no_mangle]
pub extern "C" fn n3_chunk_plan(
    source: *const n3_buffer,
    options: *const n3_chunk_options,
    out: *mut n3_buffer,
) -> n3_status {
    clear_buffer(out);
    let data = match buffer_as_slice(source) {
        Ok(value) => value,
        Err(status) => return status,
    };
    let text = match std::str::from_utf8(data) {
        Ok(value) => value,
        Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
    };
    let opts = unsafe { options.as_ref() };
    let max_chars = opts.map(|opt| opt.max_chars).unwrap_or(800);
    let overlap = opts.map(|opt| opt.overlap).unwrap_or(100);
    let plan = plan_chunks(text, max_chars, overlap);
    let payload = plan_to_json(&plan);
    set_buffer(out, payload);
    n3_status::N3_STATUS_OK
}

#[no_mangle]
pub extern "C" fn n3_exec_ir(ir: *const n3_buffer, config: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    let ir_bytes = match buffer_as_slice(ir) {
        Ok(value) => value,
        Err(status) => return status,
    };
    let ir_text = match std::str::from_utf8(ir_bytes) {
        Ok(value) => value,
        Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
    };
    let config_text = if config.is_null() {
        None
    } else {
        match buffer_as_slice(config) {
            Ok(value) => {
                if value.is_empty() {
                    None
                } else {
                    match std::str::from_utf8(value) {
                        Ok(text) => Some(text),
                        Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
                    }
                }
            }
            Err(_) => return n3_status::N3_STATUS_INVALID_ARGUMENT,
        }
    };
    let payload = match execute_ir(ir_text, config_text) {
        Ok(data) => data,
        Err(status) => return status,
    };
    set_buffer(out, payload);
    n3_status::N3_STATUS_OK
}

#[no_mangle]
pub extern "C" fn n3_free(buffer: *mut n3_buffer) {
    if buffer.is_null() {
        return;
    }
    unsafe {
        let data = (*buffer).data as *mut u8;
        let len = (*buffer).len;
        if !data.is_null() && len > 0 {
            let slice = std::ptr::slice_from_raw_parts_mut(data, len);
            drop(Box::from_raw(slice));
        }
    }
    clear_buffer(buffer);
}
