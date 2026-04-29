# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation.

This repository implements the safe planning core for the SourceOS / SociOS boot and recovery lane. It is not yet a full bootloader and deliberately does not execute host mutation in this tranche.

## What this slice does

- validates signed-boot-manifest-shaped objects before planning boot/recovery
- verifies RSA-PSS/SHA-256 manifest signatures against a trusted-key document
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

## M2 demo fixture

The repository carries a side-effect-free M2 recovery fixture under `examples/`:

- `signed_boot_manifest.recovery.json`
- `enrollment_token.recovery.json`
- `trusted_keys.recovery.json`

Run it through the planner:

```bash
python3 -m pip install -e .
nlboot-plan \
  --manifest examples/signed_boot_manifest.recovery.json \
  --token examples/enrollment_token.recovery.json \
  --trusted-keys examples/trusted_keys.recovery.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z
```

The command emits a safe plan only. Later implementation tranches can add verified artifact fetching and host execution behind explicit policy gates.

## Validation

```bash
make validate
```

The GitHub Actions validation lane runs `make validate` and a CLI smoke over the M2 fixture.
