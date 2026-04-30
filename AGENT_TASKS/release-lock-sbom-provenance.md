# Agent task: release lock, SBOM, and provenance hardening

Target agent: Codex environment for `SociOS-Linux/nlboot`; Copilot coding agent if available.

## Purpose

NLBoot now has a release workflow and release-readiness checklist. The next release-hardening slice is to make dependency locking, SBOM generation, and release provenance cleaner and reviewable.

## Scope

1. Inspect the live repository before editing.
2. Generate and commit `rust/nlboot-client/Cargo.lock` for the Rust binary application.
3. Update validation workflows so locked builds are used where appropriate.
4. Add an SBOM generation step to the release workflow if a standard lightweight action/tool can be used safely.
5. Include the SBOM in release archives and GitHub release payloads.
6. Keep provenance attestation enabled where supported.
7. Update `docs/RELEASE_READINESS_CHECKLIST.md` if the release workflow changes.

## Acceptance criteria

- `make validate` passes.
- `make rust-check` passes.
- `make rust-test` passes.
- Release workflow still builds `x86_64-unknown-linux-gnu` and `aarch64-unknown-linux-gnu` archives.
- `Cargo.lock` is committed.
- SBOM generation is either implemented or a clear blocker is documented in the PR body.
- No release URLs, hashes, or provenance claims are invented.

## Boundary

One PR only.

Do not implement real host-changing behavior in this task.

Do not change boot/recovery semantics.

Do not add secrets, tokens, credentials, signing keys, or private certificates.
