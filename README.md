# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation and Rust production-client lane.

This repository now contains three layers:

- Python reference planner and conformance harness.
- Rust `nlboot-client` usable-MVP lane for planning, artifact fetch/cache, evidence output, gated Linux handoff, and Apple Silicon M2 adapter dry-run proof.
- SourceOS lifecycle contracts for `ReleaseSet`, `BootReleaseSet`, and `LifecycleStateRecord` control-plane objects.

NLBoot is not scoped to one machine. The M2 path is the first-class proof target because it is the first real machine we are proving on. The portable protocol must also support generic UEFI/iPXE, Purism/Linux-first hardware, and VM/bootstrap targets.

## Stance

NLBoot is platform-portable.

The Python implementation remains the reference planner, conformance harness, and fast iteration surface. The production boot/recovery client matures in Rust under `rust/nlboot-client`.

See:

- `docs/RUST_STANCE_AND_MATURITY.md`
- `docs/EXECUTION_BOUNDARY.md`
- `docs/USABLE_MVP_GAP.md`
- `docs/PLATFORM_ADAPTER_MATRIX.md`
- `docs/APPLE_SILICON_M2_ADAPTER_PLAN.md`
- `docs/APPLE_SILICON_M2_ADAPTER_CONTRACT.md`
- `docs/LIFECYCLE_CONTRACTS.md`

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
- Gated `linux-kexec --load-only` path.
- Gated `linux-kexec --exec` path requiring prior load-only proof, explicit host-mutation acknowledgement, and explicit reboot acknowledgement.
- Apple Silicon M2 dry-run adapter evidence path.
- Dry-run proofs for CI and local validation.
- Refusal records for blocked paths.
- `ReleaseSet` lifecycle contract schema and M2 demo example.
- `BootReleaseSet` lifecycle contract schema and M2 recovery demo example.
- `LifecycleStateRecord` schema and signed-state transition demo example.
- Lifecycle contract validation wired into `make validate`.

## What is still intentionally gated

The production client does not yet implement:

- installer disk writes;
- rollback execution;
- real Apple Silicon boot-entry changes;
- host repair actions;
- persistent enrollment-secret storage;
- website/control-plane assignment flows.

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

## Lifecycle objects

`ReleaseSet` binds the immutable SourceOS system target to user-space closures, agent-space closures, policy bundles, BOM/SBOM refs, signing refs, rollback lineage, and evidence requirements.

`BootReleaseSet` binds a `ReleaseSet` to signed boot artifacts, the signed boot manifest, live/install/recovery channels, platform adapters, authorization requirements, offline fallback, signing refs, and proof requirements.

`LifecycleStateRecord` records state transitions such as build, sign, assign, plan, fetch, load-only, execute, attest, evaluate compliance, and rollback.

Lifecycle contracts and examples:

```text
schemas/release-set.schema.v0.1.json
schemas/boot-release-set.schema.v0.1.json
schemas/lifecycle-state-record.schema.v0.1.json
examples/release_set.m2_demo.json
examples/boot_release_set.m2_demo_recovery.json
examples/lifecycle_state_record.m2_demo_signed.json
```

Lifecycle validation:

```bash
make validate-lifecycle-contracts
```

## Usable MVP flow

Run the generic Linux/Purism/VM local usable-MVP fixture path:

```bash
make rust-exec-dry-run-fixture
```

That target performs:

1. signed manifest and token validation;
2. plan output to `/tmp/nlboot-fixture-plan.json`;
3. artifact fetch/copy through `examples/artifact_map.recovery.json`;
4. SHA-256 verification;
5. content-addressed cache write under `/tmp/nlboot-cache`;
6. evidence output under `/tmp/nlboot-evidence`;
7. dry-run `linux-kexec --load-only` proof with explicit host-mutation acknowledgement;
8. dry-run `linux-kexec --exec` proof with explicit host-mutation and reboot acknowledgements.

Run the Apple Silicon M2 adapter dry-run proof:

```bash
make rust-apple-m2-dry-run-fixture
```

That target performs:

1. signed manifest and token validation;
2. artifact fetch/cache/evidence;
3. Apple Silicon M2 adapter dry-run;
4. `adapter-plan-record.json` output;
5. `boot-entry-record.json` output.

Equivalent manual M2 adapter dry-run:

```bash
cd rust/nlboot-client

cargo run -- execute \
  --plan /tmp/nlboot-fixture-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter apple-silicon-m2 \
  --load-only \
  --dry-run \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host
```

A real `kexec --load` path removes `--dry-run` and must run with root or equivalent capability. A real `kexec --exec` path also requires the prior load-only proof and `--i-understand-this-reboots-host`. The Apple Silicon path is currently evidence-only dry run; real adapter behavior must be implemented in the Apple Silicon platform layer.

## Validation

```bash
make validate
make validate-lifecycle-contracts
make rust-check
make rust-test
make rust-run-fixture
make rust-fetch-fixture
make rust-execute-dry-run-fixture
make rust-exec-dry-run-fixture
make rust-apple-m2-dry-run-fixture
```

The GitHub Actions validation lane runs Python reference validation and the Rust usable-MVP fixture path, including the Apple Silicon M2 adapter dry-run proof.
