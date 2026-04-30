# NLBoot operator-test release handoff

This handoff records the current operator-test release state after the release-candidate workflow was proven through PR #8.

## Proven release-candidate artifact

Workflow:

```text
.github/workflows/release-candidate.yml
```

Run result:

- validation: passed
- release-candidate build: passed
- artifact upload: passed
- provenance attestation step: passed where GitHub supported it

Artifact:

```text
nlboot-client-release-candidate
```

Artifact digest:

```text
sha256:fece6f08819baa8f0f1152e42c1e7121378dc490c941d99604e6cee7854bff10
```

The release-candidate artifact is not a stable release and must not be used to publish a Homebrew formula.

## Current supported behavior

The operator-test build supports:

- signed manifest planning;
- artifact-map resolution;
- SHA-256 artifact verification;
- content-addressed cache evidence;
- Linux dry-run handoff proof;
- gated final handoff path;
- Apple Silicon M2 adapter dry-run evidence;
- refusal records for blocked unsafe paths;
- release-candidate packaging with dependency metadata.

## Current unsupported behavior

The operator-test build does not yet claim:

- real Apple Silicon boot-entry mutation;
- installer disk writes;
- rollback execution;
- recovery repair execution;
- persistent enrollment-secret storage;
- production fleet admission;
- stable Homebrew installation from a published release formula.

## Next release-hardening work

1. Add formal SBOM artifact generation.
2. Cut a tagged operator-test release only after release notes are updated.
3. Run the Homebrew template generation workflow after a real release exists.
4. Add SourceOS devtools schema-backed evidence validation.
5. Continue M2 adapter evidence normalization and platform-entry descriptor work.

## Merge/reference points

- NLBoot release-candidate proof PR: `SociOS-Linux/nlboot#8`
- SourceOS boot integration: `SourceOS-Linux/sourceos-boot#12`
- SourceOS M2 packaging spec: `SourceOS-Linux/sourceos-boot#14`
- SourceOS canonical schemas: `SourceOS-Linux/sourceos-spec#69`, `SourceOS-Linux/sourceos-spec#73`
- SourceOS devtools scaffold: `SourceOS-Linux/sourceos-devtools#2`
- Web evidence dashboard: `mdheller/socioprophet-web#21`
- Homebrew template workflow: `SocioProphet/homebrew-prophet#8`
