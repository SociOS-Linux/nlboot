# Agent task: fix Rust manifest signature canonicalization

Target: `SociOS-Linux/nlboot` PR `#8` / branch `chatgpt/release-candidate-proof`.

## Problem

The release-candidate proof PR triggered both `nlboot validate` and `nlboot release candidate` workflows. Both failed during Rust tests.

The Python reference verifier canonicalizes signed manifest payloads as compact JSON with sorted keys:

```python
json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
```

The Rust verifier currently removes `signature_hex` but serializes the remaining `serde_json::Value::Object` using the existing object order. The fixture signature was produced against the Python canonical payload, so Rust fails with:

```text
Error: signature verification failed
```

## Required fix

1. Update `rust/nlboot-client/src/main.rs` so `canonical_manifest_payload` recursively sorts object keys before serialization.
2. Preserve compact `serde_json::to_vec` output.
3. Keep array ordering unchanged.
4. Add or update a focused test if needed.
5. Rerun:

```bash
make rust-test
make rust-run-fixture
make rust-fetch-fixture
make rust-execute-dry-run-fixture
make rust-exec-dry-run-fixture
make rust-apple-m2-dry-run-fixture
```

## Suggested Rust shape

```rust
fn sort_json_value(value: &Value) -> Value {
    match value {
        Value::Object(map) => {
            let mut entries: BTreeMap<String, Value> = BTreeMap::new();
            for (key, value) in map {
                entries.insert(key.clone(), sort_json_value(value));
            }
            let mut sorted = serde_json::Map::new();
            for (key, value) in entries {
                sorted.insert(key, value);
            }
            Value::Object(sorted)
        }
        Value::Array(items) => Value::Array(items.iter().map(sort_json_value).collect()),
        other => other.clone(),
    }
}

fn canonical_manifest_payload(manifest_value: &Value) -> Result<Vec<u8>> {
    let mut unsigned = manifest_value
        .as_object()
        .cloned()
        .context("manifest must be a JSON object")?;
    unsigned.remove("signature_hex");
    Ok(serde_json::to_vec(&sort_json_value(&Value::Object(unsigned)))?)
}
```

`BTreeMap` is already imported in `main.rs`.

## Workflow fix

The release-candidate workflow also shows the Rust setup cache invoking `cargo metadata` at the repository root, which has no `Cargo.toml`.

Set `cache: false` on `actions-rust-lang/setup-rust-toolchain@v1` in:

- `.github/workflows/release-candidate.yml`
- `.github/workflows/validate.yml`
- `.github/workflows/release.yml`

or otherwise configure caching so Cargo runs from `rust/nlboot-client`.

## Acceptance criteria

- PR `#8` workflows rerun.
- Rust tests no longer fail on fixture signature verification.
- Release-candidate workflow reaches artifact assembly or fails later with a new actionable error.
- No runtime host-changing behavior is broadened.
