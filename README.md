# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation and Rust production-client lane.

This repository now contains two layers:

- Python reference planner and conformance harness.
- Rust `nlboot-client` usable-MVP lane for planning, artifact fetch/cache, evidence output, and gated Linux kexec load-only handoff.

NLBoot is not scoped to one machine. The M2 path is the first-class proof target because it is the first real machine we are proving on. The portable protocol must also support generic UEFI/iPXE, Purism/Linux-first hardware, and VM/bootstrap targets.

## Stance

NLBoot is platform-portable.

The Python implementation remains the reference planner, conformance harness, and fast iteration surface. The production boot/recovery client matures in Rust under `rust/nlboot-client`.

See:

- `docs/RUST_STANCE_AND_MATURITY.md`
- `docs/EXECUTION_BOUNDARY.md`
- `docs/USABLE_MVP_GAP.md`
- `docs/PLATFORM_ADAPTER_MATRIX.md`

## What is implemented now

- Signed boot-manifest parsing.
- RSA-PSS/SHA-256 manifest verification in Python.
- RSA-PSS/SHA-256 manifest verification in Rust.
- One-time enrollment token validation.
- `BootPlan` JSON output with `execute=false`.
- `plan --out` for durable plan records.
- Artifact map fixture.
- Local/HTTP artifact fetch path.
- SHA-256 artifact verification.
- Content-addressed cache writes.
- Evidence output for artifact cache records.
- Gated `linux-kexec --load-only` execution path.
- Dry-run execution proof for CI and local validation.
- Refusal records for blocked execution paths.

## What is still intentionally gated

The production client does not yet implement:

- `kexec --exec` jump;
- installer disk writes;
- rollback execution;
- Apple Silicon boot entry mutation;
- host repair actions;
- persistent enrollment-secret storage.

Those operations are host mutation and require explicit platform adapters, evidence emission, and review.

## Protocol objects

`SignedBootManifest` requires:

- `manifest_id`
- `boot_release_set_id`
- `base_release_set_ref`
- `boot_mode`: `installer`, `recovery`, `ephemeral`, or `bootstrap`
- `artifacts.kernel_ref`
- `artifacts.initrd_ref`
- `artifacts.rootfs_ref`
- `signature_ref` using `urn:srcos:signature:*`
- `signer_ref`
- `signature_algorithm`: `rsa-pss-sha256`
- `crypto_profile`: `fips-140-3-compatible`
- `signature_hex`: RSA-PSS/SHA-256 signature over the canonical unsigned manifest payload

`EnrollmentToken` requires:

- one-time use
- status `issued`
- unexpired `expires_at`
- matching `release_set_ref`
- matching `boot_release_set_ref`
- purpose compatible with the boot mode

`BootPlan` is emitted only after manifest verification and token validation. It includes:

- the selected plan action
- boot and release-set references
- artifact references
- signature and crypto profile metadata
- policy reference for the boot mode
- safe planning operations allowed by that boot mode
- proof requirements the eventual executor must satisfy
- offline fallback posture
- `execute=false`

## Usable MVP flow

Run the full local usable-MVP fixture path:

```bash
make rust-execute-dry-run-fixture
```

That target performs:

1. signed manifest and token validation;
2. plan output to `/tmp/nlboot-fixture-plan.json`;
3. artifact fetch/copy through `examples/artifact_map.recovery.json`;
4. SHA-256 verification;
5. content-addressed cache write under `/tmp/nlboot-cache`;
6. evidence output under `/tmp/nlboot-evidence`;
7. dry-run `linux-kexec --load-only` proof with explicit host-mutation acknowledgement.

Equivalent manual flow:

```bash
cd rust/nlboot-client

cargo run -- plan \
  --manifest ../../examples/signed_boot_manifest.recovery.json \
  --token ../../examples/enrollment_token.recovery.json \
  --trusted-keys ../../examples/trusted_keys.recovery.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z \
  --out /tmp/nlboot-fixture-plan.json

cargo run -- fetch \
  --plan /tmp/nlboot-fixture-plan.json \
  --artifact-map ../../examples/artifact_map.recovery.json \
  --cache /tmp/nlboot-cache \
  --evidence /tmp/nlboot-evidence

cargo run -- execute \
  --plan /tmp/nlboot-fixture-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter linux-kexec \
  --load-only \
  --dry-run \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host
```

A real `kexec --load` path removes `--dry-run` and must run with root or equivalent capability. `kexec --exec` is intentionally not implemented yet.

## Validation

```bash
make validate
make rust-check
make rust-test
make rust-run-fixture
make rust-fetch-fixture
make rust-execute-dry-run-fixture
```

The GitHub Actions validation lane runs Python reference validation and the Rust usable-MVP fixture path.
