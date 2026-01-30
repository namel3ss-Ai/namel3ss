#ifndef NAMEL3SS_NATIVE_H
#define NAMEL3SS_NATIVE_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum n3_status {
    N3_STATUS_OK = 0,
    N3_STATUS_NOT_IMPLEMENTED = 1,
    N3_STATUS_INVALID_ARGUMENT = 2,
    N3_STATUS_INVALID_STATE = 3,
    N3_STATUS_ERROR = 4
} n3_status;

typedef struct n3_buffer {
    const uint8_t *data;
    size_t len;
} n3_buffer;

typedef struct n3_chunk_options {
    uint32_t max_chars;
    uint32_t overlap;
} n3_chunk_options;

n3_status n3_native_info(n3_buffer *out);

n3_status n3_scan(const n3_buffer *source, n3_buffer *out);

n3_status n3_hash(const n3_buffer *source, n3_buffer *out);

n3_status n3_normalize(const n3_buffer *source, n3_buffer *out);

n3_status n3_chunk_plan(const n3_buffer *source, const n3_chunk_options *options, n3_buffer *out);

void n3_free(n3_buffer *buffer);

#ifdef __cplusplus
}
#endif

#endif
