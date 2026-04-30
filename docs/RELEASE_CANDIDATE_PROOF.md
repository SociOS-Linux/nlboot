# NLBoot Release-Candidate Proof

This document exists to exercise the release-candidate workflow through a normal pull-request path.

The release-candidate workflow is expected to:

- run the full NLBoot validation suite;
- generate a dependency lockfile in the workflow environment;
- build a locked `nlboot-client` release candidate for `x86_64-unknown-linux-gnu`;
- emit dependency metadata through `cargo metadata --locked`;
- package a release-candidate archive;
- write a SHA-256 checksum;
- attach provenance where GitHub supports it;
- upload the artifact without publishing a stable GitHub release.

This proof PR must not change NLBoot runtime behavior. It is release-process validation only.

## Expected workflow

```text
.github/workflows/release-candidate.yml
```

## Completion condition

This proof is complete when the release-candidate workflow runs on the PR and either:

1. succeeds and uploads the release-candidate artifact; or
2. fails with actionable logs that can be fixed in a follow-up release-hardening PR.
