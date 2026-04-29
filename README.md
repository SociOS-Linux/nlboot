# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation.

This repository implements the safe planning core for the SourceOS / SociOS boot and recovery lane. It is not yet a full bootloader and deliberately does not execute host mutation in this tranche.

## What this slice does

- validates signed-boot-manifest-shaped objects before planning boot/recovery
- verifies RSA-PSS/SHA-256 manifest signatures against a trusted-key document
- validates one-time enrollment token intent, expiry, audience, and release/boot-release binding
- validates optional signed `boot_menu` data for boot-picker / PXE-style recovery and rollback parity
- produces a boot plan as JSON
- records `execute=false` in produced plans
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

`SignedBootManifest` may also include `boot_menu`:

- `boot_menu.menu_id`
- `boot_menu.default_entry_id`
- `boot_menu.entries[]`
- each entry declares `entry_id`, `label`, `boot_release_set_id`, `release_set_ref`, `boot_mode`, and `role`
- supported roles are `normal`, `recovery`, `installer`, `rollback`, `ephemeral`, and `bootstrap`
- rollback entries must explicitly set `rollback_eligible=true`
- the default menu entry must match the manifest boot release, base release, and boot mode

The `boot_menu` object is part of the signed manifest payload. This gives SourceOS a planning contract for Apple-Silicon boot-picker entries and UEFI/PXE-style menu entries without performing host mutation in this tranche.

`EnrollmentToken` requires:

- one-time use
- status `issued`
- unexpired `expires_at`
- matching `release_set_ref`
- matching `boot_release_set_ref`
- purpose compatible with the boot mode

## M2 demo fixture

The repository carries a side-effect-free M2 recovery fixture under `examples/m2-demo/`:

- `manifest.recovery.json`
- `enrollment-token.recovery.json`
- `trusted-keys.json`

Run it through the planner:

```bash
python3 -m pip install -e .
nlboot-plan \
  --manifest examples/m2-demo/manifest.recovery.json \
  --token examples/m2-demo/enrollment-token.recovery.json \
  --trusted-keys examples/m2-demo/trusted-keys.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z
```

The command emits a safe plan only. Later implementation tranches can add verified artifact fetching and host execution behind explicit policy gates.

## Validation

```bash
make validate
```

The GitHub Actions validation lane runs `make validate` and a CLI smoke over the M2 fixture.
