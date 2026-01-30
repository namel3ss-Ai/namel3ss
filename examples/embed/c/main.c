#include <stdio.h>
#include <string.h>

#include "namel3ss_native.h"

int main(void) {
    const char *input = "embed-check";
    n3_buffer source = {(const uint8_t *)input, strlen(input)};
    n3_buffer output = {0};

    n3_status status = n3_hash(&source, &output);
    if (status != N3_STATUS_OK) {
        return 1;
    }

    if (output.data != NULL && output.len > 0) {
        fwrite(output.data, 1, output.len, stdout);
    }

    n3_free(&output);
    return 0;
}
