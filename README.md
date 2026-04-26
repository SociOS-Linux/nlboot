# nlboot

`nlboot` is the SourceOS network/live/recovery boot protocol reference implementation.

This repository implements the safe planning core for the SourceOS / SociOS boot and recovery lane. It is not yet a full bootloader and deliberately does not execute host mutation in this tranche.

## What this slice does

- validates signed-boot-manifest-shaped objects before planning boot/recovery
- validates one-time enrollment token intent, expiry, audience, and release/boot-release binding
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

`EnrollmentToken` requires:

- one-time use
- status `issued`
- unexpired `expires_at`
- matching `release_set_ref`
- matching `boot_release_set_ref`
- purpose compatible with the boot mode

## Usage

```bash
python3 -m pip install -e .
nlboot-plan --manifest manifest.json --token token.json
```

The command emits a safe plan only. Later implementation tranches can add verified artifact fetching and host execution behind explicit policy gates.

## Validation

```bash
make validate
```
