# Sandbox User Write Fail

This invariant fails if a sandboxed user tool can write to the filesystem
without being blocked and traced with a denied capability_check.
