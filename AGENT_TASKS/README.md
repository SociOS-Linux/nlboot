# NLBoot agent task index

GitHub Issues are disabled for this repository. Use these repo-local task packets as the work queue.

## Operating rules

- One task packet, one branch, one PR.
- Inspect the live repository before editing.
- Keep scope bounded to the task packet.
- Include validation evidence in the PR body.
- Do not add secrets, tokens, credentials, private keys, or host-specific boot secrets.
- Do not broaden boot, install, recovery, rollback, or host-changing behavior without explicit task scope.

## Required validation baseline

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

## Active tasks

1. `release-lock-sbom-provenance.md`
   - Generate and commit `rust/nlboot-client/Cargo.lock`.
   - Harden release workflow around locked builds.
   - Add SBOM generation if practical.
   - Preserve existing boot/recovery behavior.

2. `gated-kexec-exec.md`
   - Historical task packet for final handoff gating.
   - Much of this is implemented; use only to verify gaps before creating new work.

3. `apple-silicon-adapter-dry-run.md`
   - Historical task packet for M2 dry-run evidence adapter.
   - Much of this is implemented; use only to verify gaps before creating new work.

4. `usable-mvp-fetch-kexec.md`
   - Historical usable-MVP packet.
   - Plan/fetch/cache/evidence/dry-run paths are implemented; use only for gap review.

## Current preferred task

Start with `release-lock-sbom-provenance.md`.

## PR requirements

Each PR must include:

- task packet referenced;
- files changed;
- commands run;
- pass/fail summary;
- known gaps;
- anything blocked.
