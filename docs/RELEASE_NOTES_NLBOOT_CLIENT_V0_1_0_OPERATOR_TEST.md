# NLBoot Client v0.1.0 Operator-Test Release Notes Draft

Status: draft

This release note is prepared for the first operator-test release of `nlboot-client`. It must be reviewed before a tag is cut.

## Release purpose

`nlboot-client v0.1.0` is an operator-test release for validating the SourceOS/NLBoot planning, artifact verification, evidence, and dry-run adapter paths.

It is not a production fleet release.

## Supported behavior

This release is intended to support:

- signed boot-manifest parsing;
- RSA-PSS/SHA-256 manifest verification;
- one-time enrollment-token validation;
- durable `BootPlan` output;
- local artifact-map resolution;
- SHA-256 artifact verification;
- content-addressed cache writes;
- artifact cache evidence records;
- Linux load-only dry-run proof;
- gated final handoff proof path;
- Apple Silicon M2 adapter dry-run evidence;
- refusal records for blocked execution paths;
- release-candidate package generation;
- dependency metadata generation;
- SPDX-style SBOM generation;
- provenance attestation where GitHub supports it.

## Explicit non-goals

This release does not claim support for:

- real Apple Silicon boot-entry changes;
- installer disk writes;
- rollback execution;
- recovery repair execution;
- persistent enrollment-secret storage;
- production fleet admission;
- stable Homebrew installation from a published formula.

## Release artifacts expected

A tagged release must include:

- `nlboot-client-nlboot-client-v0.1.0-x86_64-unknown-linux-gnu.tar.gz`
- `nlboot-client-nlboot-client-v0.1.0-x86_64-unknown-linux-gnu.tar.gz.sha256`
- `nlboot-client-nlboot-client-v0.1.0-aarch64-unknown-linux-gnu.tar.gz`
- `nlboot-client-nlboot-client-v0.1.0-aarch64-unknown-linux-gnu.tar.gz.sha256`
- `nlboot-client-nlboot-client-v0.1.0-x86_64-unknown-linux-gnu-sbom.spdx.json`
- `nlboot-client-nlboot-client-v0.1.0-x86_64-unknown-linux-gnu-sbom.spdx.json.sha256`
- `nlboot-client-nlboot-client-v0.1.0-aarch64-unknown-linux-gnu-sbom.spdx.json`
- `nlboot-client-nlboot-client-v0.1.0-aarch64-unknown-linux-gnu-sbom.spdx.json.sha256`
- `SHA256SUMS`

Each archive must include:

- `nlboot-client`
- `Cargo.lock`
- `cargo-metadata.json`
- `sbom.spdx.json`
- `release-manifest.json`
- `README.md`
- `RELEASE_AND_INSTALL.md`

## Validation required before tag

The release commit must pass:

```bash
make validate
make rust-check
make rust-test
make rust-run-fixture
make rust-fetch-fixture
make rust-execute-dry-run-fixture
make rust-exec-dry-run-fixture
make rust-apple-m2-dry-run-fixture
```

The release-candidate workflow must also pass and upload the `nlboot-client-release-candidate` artifact.

## Integration references

- SourceOS boot integration: `SourceOS-Linux/sourceos-boot#12`
- SourceOS M2 Recovery/Installer packaging spec: `SourceOS-Linux/sourceos-boot#14`
- SourceOS canonical NLBoot schemas: `SourceOS-Linux/sourceos-spec#69`
- SourceOS lifecycle schemas: `SourceOS-Linux/sourceos-spec#73`
- SourceOS devtools CLI scaffold: `SourceOS-Linux/sourceos-devtools#2`
- SocioProphet Web evidence dashboard: `mdheller/socioprophet-web#21`
- Homebrew release template workflow: `SocioProphet/homebrew-prophet#8`

## Homebrew status

The Homebrew tap contains a release-template workflow for `nlboot-client`. No active formula should be published until the real release artifacts and SHA-256 values exist.

## Review checklist

Before tagging:

- confirm release-candidate workflow passed after SBOM wiring;
- confirm tagged release workflow still emits SBOM artifacts;
- confirm release notes do not claim unsupported host-changing behavior;
- confirm Homebrew generation workflow will consume real artifact URLs and hashes;
- confirm SourceOS devtools can inspect or validate local NLBoot evidence records, or mark that integration as pending.
