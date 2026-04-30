# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation.

This repository implements the safe planning core for the SourceOS / SociOS boot and recovery lane. It is not yet a full bootloader and deliberately does not execute host mutation in this tranche.

## Stance

NLBoot is platform-portable. The M2 path is the first-class proof target because it is the first real machine we are proving on, but NLBoot is not scoped to one device.

The current Python implementation remains the reference planner, conformance harness, and fast iteration surface. The production boot/recovery client should mature in Rust under `rust/nlboot-client`.

See `docs/RUST_STANCE_AND_MATURITY.md` for the language and maturity plan.

## What this slice does

- validates signed-boot-manifest-shaped objects before planning boot/recovery
- verifies RSA-PSS/SHA-256 manifest signatures against a trusted-key document in the Python reference planner
- validates one-time enrollment token intent, expiry, audience, and release/boot-release binding
- produces a boot plan as JSON
- records `execute=false` in produced plans
- emits SourceOS control-plane metadata in boot plans:
  - `policy_ref`
  - `allowed_operations`
  - `proof_requirements`
  - `offline_fallback`
- never downloads artifacts, writes disks, calls `kexec`, or mutates a host in this reference slice

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

The planner is intentionally conservative. It creates an authorized plan record, not a host-mutating execution path.

## Rust production-client lane

The Rust lane lives under `rust/nlboot-client`.

Current target:

```bash
make rust-check
make rust-run-fixture
```

The Rust scaffold validates manifest shape and token binding and emits an `execute=false` plan. RSA-PSS/SHA-256 signature verification parity is required before Rust is production-ready.

## M2 demo fixture

The repository carries a side-effect-free M2 recovery fixture under `examples/`:

- `signed_boot_manifest.recovery.json`
- `enrollment_token.recovery.json`
- `trusted_keys.recovery.json`

Run it through the Python reference planner:

```bash
python3 -m pip install -e .
nlboot-plan \
  --manifest examples/signed_boot_manifest.recovery.json \
  --token examples/enrollment_token.recovery.json \
  --trusted-keys examples/trusted_keys.recovery.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z
```

Run it through the Rust scaffold:

```bash
make rust-run-fixture
```

Both commands emit safe plans only. Later implementation tranches can add verified artifact fetching and host execution behind explicit policy gates.

## Validation

```bash
make validate
make rust-check
```

The GitHub Actions validation lane runs Python reference validation and Rust scaffold checks.
