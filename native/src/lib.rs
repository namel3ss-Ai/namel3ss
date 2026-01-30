#![allow(non_camel_case_types)]

use core::ptr;

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

fn clear_buffer(out: *mut n3_buffer) {
    if out.is_null() {
        return;
    }
    unsafe {
        (*out).data = ptr::null();
        (*out).len = 0;
    }
}

#[no_mangle]
pub extern "C" fn n3_native_info(out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    n3_status::N3_STATUS_NOT_IMPLEMENTED
}

#[no_mangle]
pub extern "C" fn n3_scan(_source: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    n3_status::N3_STATUS_NOT_IMPLEMENTED
}

#[no_mangle]
pub extern "C" fn n3_hash(_source: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    n3_status::N3_STATUS_NOT_IMPLEMENTED
}

#[no_mangle]
pub extern "C" fn n3_normalize(_source: *const n3_buffer, out: *mut n3_buffer) -> n3_status {
    clear_buffer(out);
    n3_status::N3_STATUS_NOT_IMPLEMENTED
}

#[no_mangle]
pub extern "C" fn n3_free(buffer: *mut n3_buffer) {
    clear_buffer(buffer);
}
