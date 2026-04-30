# NLBoot release-readiness checklist

This checklist defines the minimum bar before publishing an `nlboot-client` release artifact for operator testing.

## 1. Validation gate

All validation targets must pass on the release commit:

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

The release workflow must also run these targets on the native Linux build before packaging artifacts.

## 2. Release workflow gate

The release workflow must produce:

- `nlboot-client-<version>-x86_64-unknown-linux-gnu.tar.gz`
- `nlboot-client-<version>-aarch64-unknown-linux-gnu.tar.gz`
- per-archive `.sha256` files
- combined `SHA256SUMS`
- `release-manifest.json` inside each archive
- `Cargo.lock` inside each archive
- provenance attestation where GitHub supports it

## 3. Release manifest gate

Each release manifest must include:

- artifact name;
- version;
- target triple;
- commit SHA;
- source repository;
- validation command list;
- host-mutation default posture;
- Apple Silicon adapter posture;
- Cargo lock inclusion flag.

## 4. Operator documentation gate

The release must reference:

- `README.md`
- `docs/DRY_RUN_OPERATOR_QUICKSTART.md`
- `docs/RELEASE_AND_INSTALL.md`
- `docs/EXECUTION_BOUNDARY.md`
- `docs/APPLE_SILICON_M2_ADAPTER_CONTRACT.md`

The operator quickstart must describe dry-run proof only. Real host-changing operation must remain gated by explicit commands, root/capability, evidence records, and review.

## 5. Homebrew gate

The Homebrew formula must not invent release URLs or hashes.

Before publishing a formula update:

1. publish a GitHub release;
2. copy actual archive URLs;
3. copy actual SHA-256 values;
4. run Homebrew formula validation;
5. open a PR in `SocioProphet/homebrew-prophet` with validation evidence.

## 6. SourceOS integration gate

The release is not SourceOS-integrated until:

- `SourceOS-Linux/sourceos-spec` has canonical object schemas for NLBoot evidence records;
- `SourceOS-Linux/sourceos-boot` has integration docs/fixtures consuming those objects;
- `mdheller/socioprophet-web` can display mock NLBoot evidence records in the Vue shell;
- `SocioProphet/homebrew-prophet` has a formula/update path.

## 7. Risk boundary

The following are not release-complete until separately reviewed and proven:

- real Apple Silicon boot-entry changes;
- installer disk writes;
- rollback execution;
- recovery repair execution;
- persistent enrollment-secret storage;
- production fleet admission.

Release artifacts may be published for operator dry-run testing before these exist, but they must not claim those capabilities.

## 8. Completion definition

An NLBoot operator-test release is complete when:

- CI passes;
- release workflow publishes archives and checksums;
- provenance attestation is present or explicitly noted as unavailable;
- release notes state exact supported and unsupported behaviors;
- Homebrew formula PR exists or is merged;
- SourceOS schema/boot/web integration issues are linked from the release notes.
