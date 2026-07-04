# Agent Operating Instructions

Work issue-first.

Rules:
- One repo, one issue, one PR.
- Inspect the live repository before editing.
- Keep scope bounded to the issue body or repo-local task packet.
- Do not broaden scope without asking in the issue.
- Do not touch unrelated files.
- Do not claim production readiness unless acceptance criteria prove it.
- Include validation evidence in the PR body.
- Leave known gaps explicit.

PR body must include:
- What changed.
- Exact commands run.
- Pass/fail output summary.
- Known gaps.
- Anything blocked.

Never:
- Commit secrets, tokens, credentials, or private keys.
- Invent release URLs, checksums, SBOMs, or provenance.
- Admit runtimes to production from fixture proofs.
- Claim live ingestion when only fixture validation exists.
- Claim safety-critical authority from advisory data.

NLBoot-specific rules:
- Preserve planner, fetch, evidence, and adapter boundaries.
- Dry-run evidence paths come before real host-changing behavior.
- Real boot, install, recovery, or handoff behavior must be explicitly gated and reviewed.
- M2 is first-class proof hardware, not the product boundary.
- Keep portable core separate from platform adapters.
- Do not claim Apple Silicon boot-entry mutation exists unless implemented and validated.
- Do not broaden linux-kexec, Apple Silicon, installer, recovery, or rollback behavior without tests and documentation.

Validation commands:
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
