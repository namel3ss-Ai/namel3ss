use std::os::raw::c_uchar;

#[repr(C)]
#[derive(Copy, Clone, Debug, PartialEq, Eq)]
enum n3_status {
    N3_STATUS_OK = 0,
    N3_STATUS_NOT_IMPLEMENTED = 1,
    N3_STATUS_INVALID_ARGUMENT = 2,
    N3_STATUS_INVALID_STATE = 3,
    N3_STATUS_ERROR = 4,
}

#[repr(C)]
#[derive(Copy, Clone, Debug)]
struct n3_buffer {
    data: *const c_uchar,
    len: usize,
}

#[link(name = "namel3ss_native")]
extern "C" {
    fn n3_hash(source: *const n3_buffer, out: *mut n3_buffer) -> n3_status;
    fn n3_free(buffer: *mut n3_buffer);
}

fn main() {
    let input = b"embed-check";
    let source = n3_buffer {
        data: input.as_ptr(),
        len: input.len(),
    };
    let mut output = n3_buffer {
        data: std::ptr::null(),
        len: 0,
    };

    let status = unsafe { n3_hash(&source, &mut output) };
    if status != n3_status::N3_STATUS_OK {
        std::process::exit(1);
    }

    if !output.data.is_null() && output.len > 0 {
        let slice = unsafe { std::slice::from_raw_parts(output.data, output.len) };
        let text = std::str::from_utf8(slice).unwrap_or("");
        print!("{}", text);
    }

    unsafe {
        n3_free(&mut output);
    }
}
