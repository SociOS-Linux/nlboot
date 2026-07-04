# NLBoot Rust lane

This directory is the production-client lane for NLBoot.

The current Python implementation remains the reference planner and conformance harness. The Rust lane exists to produce a small, memory-safe, compiled boot/recovery client suitable for initramfs, recovery images, live installers, and bootstrap media.

## Non-negotiable boundary

The Rust client must remain side-effect free until explicit execution gates are specified and reviewed.

Initial Rust parity target:

- read a signed boot manifest JSON file;
- read an enrollment token JSON file;
- read trusted keys JSON file;
- verify manifest shape;
- verify token intent and release binding;
- emit a BootPlan JSON object with `execute: false`;
- refuse unsupported boot modes, expired tokens, mismatched refs, and missing artifacts.

Cryptographic signature verification is a production requirement, but the first scaffold may implement structure and token parity before RSA-PSS/SHA-256 parity lands. Any scaffold that does not verify signatures must clearly mark itself as incomplete and must never be used as a production executor.

## Target command

```bash
nlboot-client plan \
  --manifest examples/signed_boot_manifest.recovery.json \
  --token examples/enrollment_token.recovery.json \
  --trusted-keys examples/trusted_keys.recovery.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z
```

## Production target

The Rust implementation should eventually become the released `nlboot-client` binary. Python should remain the conformance/reference implementation.

## Platform model

The Rust lane implements the portable core only:

- BootReleaseSet / signed manifest validation;
- EnrollmentToken validation;
- BootPlan generation;
- BootProof emission;
- last-known-good fallback policy;
- refusal behavior.

Platform-specific execution belongs behind platform adaptation layers:

- Apple Silicon / M2 recovery-install entry;
- generic UEFI/iPXE/netboot;
- Purism/Linux-first hardware;
- VM/bootstrap target.
