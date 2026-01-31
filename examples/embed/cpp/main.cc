#include <cstdio>
#include <cstring>

#include "namel3ss_native.h"

int main() {
    const char *input = "embed-check";
    n3_buffer source = {reinterpret_cast<const uint8_t *>(input), std::strlen(input)};
    n3_buffer output = {0};

    n3_status status = n3_hash(&source, &output);
    if (status != N3_STATUS_OK) {
        return 1;
    }

    if (output.data != nullptr && output.len > 0) {
        std::fwrite(output.data, 1, output.len, stdout);
    }

    n3_free(&output);
    return 0;
}
