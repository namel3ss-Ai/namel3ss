# Rust Embed

Build the native library and compile the example from the repo root:

```
# Build native library
cargo build --release --manifest-path native/Cargo.toml

# Compile example (adjust the library directory as needed)
rustc examples/embed/rust/main.rs -L native/target/release -l namel3ss_native -o embed_rust
```

Run with a library search path that points to the native build:

```
LD_LIBRARY_PATH=native/target/release ./embed_rust
```
