# NLBoot release and install plan

This document defines the release and installation path for `nlboot-client`.

The goal is to make NLBoot usable as a signed, downloadable, testable operator binary while preserving its safety gates.

## Release artifact

Primary binary:

- `nlboot-client`

Initial target platforms:

- `x86_64-unknown-linux-gnu`
- `aarch64-unknown-linux-gnu`

Future targets:

- musl/static Linux targets where crypto/TLS dependencies permit;
- SourceOS Recovery Environment image integration;
- Apple Silicon M2 recovery/installer adapter bundle.

## Release contents

Each release should publish:

- `nlboot-client-<version>-x86_64-unknown-linux-gnu.tar.gz`
- `nlboot-client-<version>-aarch64-unknown-linux-gnu.tar.gz`
- `SHA256SUMS`
- `SHA256SUMS.sig` or release attestation when available
- `sbom.spdx.json` or equivalent SBOM
- source archive

## Required local validation before release

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

## Install path

Manual install:

```bash
cargo install --path rust/nlboot-client
```

Operator dry-run proof:

```bash
nlboot-client plan \
  --manifest examples/signed_boot_manifest.recovery.json \
  --token examples/enrollment_token.recovery.json \
  --trusted-keys examples/trusted_keys.recovery.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z \
  --out /tmp/nlboot-fixture-plan.json

nlboot-client fetch \
  --plan /tmp/nlboot-fixture-plan.json \
  --artifact-map examples/artifact_map.recovery.json \
  --cache /tmp/nlboot-cache \
  --evidence /tmp/nlboot-evidence

nlboot-client execute \
  --plan /tmp/nlboot-fixture-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter linux-kexec \
  --load-only \
  --dry-run \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host
```

## Real host mutation rules

Real host-changing paths require:

- verified signed manifest;
- trusted signing key;
- valid enrollment token or device assignment;
- verified artifact hashes;
- cache evidence;
- explicit acknowledgement flag;
- root or equivalent capability;
- evidence directory;
- adapter-specific policy.

For final handoff:

- prior load-only proof is required;
- explicit reboot acknowledgement is required;
- root or equivalent capability is required;
- `--dry-run` must be omitted intentionally.

## Homebrew / SourceOS devtools path

The eventual operator path should be:

```bash
brew tap SocioProphet/prophet
brew install nlboot-client
```

SourceOS Developer Tools should also install `nlboot-client` as part of the boot/recovery profile.

## Not release-ready until

NLBoot is not considered release-ready until:

- CI passes on all validation targets;
- release archives are reproducible enough for operator use;
- SHA-256 sums are published;
- SBOM is generated;
- release provenance/attestation is configured;
- README and operator docs match the binary behavior;
- real host-changing operations are clearly gated and refusal-tested.
