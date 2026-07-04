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

## 2. Release-candidate gate

Before publishing a tagged release, run the release-candidate workflow:

```text
.github/workflows/release-candidate.yml
```

The release-candidate workflow must produce:

- `nlboot-client-rc-x86_64-unknown-linux-gnu.tar.gz`
- `nlboot-client-rc-x86_64-unknown-linux-gnu.tar.gz.sha256`
- `release-candidate-manifest.json` inside the archive
- `Cargo.lock` inside the archive
- `cargo-metadata.json` inside the archive
- `sbom.spdx.json` inside the archive
- provenance attestation where GitHub supports it

Release-candidate artifacts are for validation only. They must not be treated as stable releases and must not drive Homebrew formula publication.

## 3. Release workflow gate

The release workflow must produce:

- `nlboot-client-<version>-x86_64-unknown-linux-gnu.tar.gz`
- `nlboot-client-<version>-aarch64-unknown-linux-gnu.tar.gz`
- per-archive `.sha256` files
- combined `SHA256SUMS`
- `release-manifest.json` inside each archive
- `Cargo.lock` inside each archive
- `cargo-metadata.json` inside each archive
- `sbom.spdx.json` inside each archive
- `nlboot-client-<version>-<target>-sbom.spdx.json`
- `nlboot-client-<version>-<target>-sbom.spdx.json.sha256`
- provenance attestation where GitHub supports it

## 4. Release manifest gate

Each release manifest must include:

- artifact name;
- version;
- target triple;
- commit SHA;
- source repository;
- validation command list;
- host-mutation default posture;
- Apple Silicon adapter posture;
- Cargo lock inclusion flag;
- dependency metadata inclusion flag;
- SBOM inclusion flag.

## 5. Operator documentation gate

The release must reference:

- `README.md`
- `docs/DRY_RUN_OPERATOR_QUICKSTART.md`
- `docs/RELEASE_AND_INSTALL.md`
- `docs/EXECUTION_BOUNDARY.md`
- `docs/APPLE_SILICON_M2_ADAPTER_CONTRACT.md`
- `docs/OPERATOR_TEST_RELEASE_HANDOFF.md`

The operator quickstart must describe dry-run proof only. Real host-changing operation must remain gated by explicit commands, root/capability, evidence records, and review.

## 6. Homebrew gate

The Homebrew formula must not invent release URLs or hashes.

Before publishing a formula update:

1. publish a GitHub release;
2. copy actual archive URLs;
3. copy actual SHA-256 values;
4. run Homebrew formula validation;
5. open a PR in `SocioProphet/homebrew-prophet` with validation evidence.

## 7. SourceOS integration gate

The release is not SourceOS-integrated until:

- `SourceOS-Linux/sourceos-spec` has canonical object schemas for NLBoot evidence records;
- `SourceOS-Linux/sourceos-boot` has integration docs/fixtures consuming those objects;
- `mdheller/socioprophet-web` can display mock NLBoot evidence records in the Vue shell;
- `SourceOS-Linux/sourceos-devtools` can inspect or validate local NLBoot evidence records;
- `SocioProphet/homebrew-prophet` has a formula/update path.

## 8. Risk boundary

The following are not release-complete until separately reviewed and proven:

- real Apple Silicon boot-entry changes;
- installer disk writes;
- rollback execution;
- recovery repair execution;
- persistent enrollment-secret storage;
- production fleet admission.

Release artifacts may be published for operator dry-run testing before these exist, but they must not claim those capabilities.

## 9. Completion definition

An NLBoot operator-test release is complete when:

- CI passes;
- release-candidate workflow passes;
- release workflow publishes archives and checksums;
- provenance attestation is present or explicitly noted as unavailable;
- dependency metadata is present;
- SBOM artifact is present;
- release notes state exact supported and unsupported behaviors;
- Homebrew formula PR exists or is merged;
- SourceOS schema/boot/web/devtools integration issues are linked from the release notes.
