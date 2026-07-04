# NLBoot Rust stance and maturity plan

## Position

NLBoot should remain protocol-first and platform-portable. The M2 path is the first-class test bed because it is the first machine we are proving on, but NLBoot is not an M2-only project.

The production boot/recovery client should move toward Rust.

The current Python implementation should remain as the reference planner, conformance harness, fixture generator, and fast iteration surface until the Rust implementation reaches parity.

## Why Rust is the right production direction

NLBoot sits in the boot and recovery lane. That lane eventually needs to run in constrained, security-sensitive environments such as initramfs, recovery images, live installers, and possibly tiny bootstrap media.

Rust is the right production language for that layer because it supports:

- a small compiled binary suitable for initramfs/recovery environments;
- memory safety without a garbage-collected runtime;
- explicit error handling for security-critical validation paths;
- good cross-compilation posture for Linux targets;
- strong library support for TLS, signatures, hashing, JSON/CBOR-style manifests, and CLI tooling;
- cleaner packaging as release artifacts and Homebrew/devtools-installed binaries.

## What stays in Python

The Python implementation is still valuable and should not be thrown away.

It should remain the reference implementation for:

- protocol design iteration;
- canonical test fixtures;
- negative test vectors;
- schema conformance tests;
- comparison against the Rust client;
- control-plane-side validation examples.

The Python planner must remain side-effect free unless a future change explicitly introduces execution gates.

## Current maturity

Current maturity is M2.

NLBoot currently has:

- safe boot planning;
- RSA-PSS/SHA-256 manifest verification;
- one-time enrollment token validation;
- `execute=false` boot plans;
- M2 recovery fixtures;
- a `make validate` lane.

This is a standards/reference slice, not a production boot executor.

## Target maturity path

### M3: hardened reference planner

M3 requires:

- schema alignment with `SourceOS-Linux/sourceos-spec`;
- negative tests for invalid signature, expired token, mismatched release refs, mismatched boot-release refs, and unsupported boot mode;
- boot proof fixtures;
- clearer docs for portable core versus platform adaptation layer;
- no host mutation path.

### M4: production Rust boot client

M4 requires a Rust implementation of the production client:

- `nlboot` or `nlboot-client` binary;
- manifest verification parity with Python;
- token validation parity with Python;
- boot plan output parity with Python;
- signed release artifacts;
- checksums;
- SBOM;
- provenance/attestation where supported;
- Homebrew/devtools packaging path.

### M5: operational boot and recovery readiness

M5 requires operational proof across at least two platform adaptation layers:

- Apple Silicon / M2 path using the SourceOS recovery/install entry model;
- generic UEFI/Purism-style path using secure netboot or bootstrap media semantics.

M5 also requires:

- last-known-good fallback proof;
- recovery/rollback proof;
- device claim and enrollment proof;
- evidence emission;
- compatibility matrix;
- clear refusal behavior for unsigned or unauthorized artifacts.

## Platform model

NLBoot has a portable core and platform adaptation layers.

Portable core:

- BootReleaseSet manifest validation;
- EnrollmentToken validation;
- DeviceClaim handling;
- BootPlan generation;
- BootProof emission;
- artifact reference and signature policy;
- offline fallback policy.

Platform adaptation layers:

- Apple Silicon / M2 recovery/install integration;
- generic UEFI/iPXE/netboot integration;
- Purism/Linux-first hardware integration;
- VM/bootstrap integration.

The portable core must not encode M2-specific assumptions. M2-specific behavior belongs in the Apple Silicon platform adaptation layer.

## Execution boundary

NLBoot must keep planning and execution separate.

The current planner emits `execute=false`. Future execution support must be introduced behind explicit policy gates and separate review.

Host mutation operations such as artifact fetch, kexec, disk writes, boot entry updates, and rollback execution must require:

- signed manifest verification;
- authorized token or device assignment;
- platform policy approval;
- proof emission;
- refusal on mismatch or missing trust.

## Recommendation

Use Python for reference and control-plane conformance.

Use Rust for the production boot/recovery client.

Treat M2 as the first-class proof target, not the boundary of the project.
