# C Embed

Build the native library and compile the example from the repo root:

```
# Build native library
cargo build --release --manifest-path native/Cargo.toml

# Compile example (adjust the library directory as needed)
cc -I native/include examples/embed/c/main.c -L native/target/release -l namel3ss_native -o embed_c
```

Run with a library search path that points to the native build:

```
LD_LIBRARY_PATH=native/target/release ./embed_c
```
