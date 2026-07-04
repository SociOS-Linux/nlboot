# Agent task: Rust RSA-PSS/SHA-256 signature parity

Target agent: Codex environment for `SociOS-Linux/nlboot`; Copilot coding agent if available.

## Purpose

The Rust `nlboot-client` scaffold currently validates manifest shape and enrollment-token binding, then emits a safe `execute=false` boot plan. It does not yet implement RSA-PSS/SHA-256 signature verification parity with the Python reference planner.

This task closes that gap without adding host mutation.

## Scope

1. Inspect the Python reference implementation in `src/nlboot/verify.py` and `src/nlboot/cli.py`.
2. Implement Rust verification parity for:
   - canonical unsigned manifest payload;
   - trusted key lookup by `signer_ref`;
   - RSA-PSS/SHA-256 verification;
   - `--require-fips` enforcement of `rsa-pss-sha256` and `fips-140-3-compatible`.
3. Add Rust tests or fixture checks for:
   - valid M2 recovery fixture;
   - invalid signature;
   - unknown signer;
   - algorithm mismatch;
   - expired token;
   - mismatched release refs;
   - unsupported boot mode.
4. Keep output parity close to the Python reference planner where practical.
5. Add `Cargo.lock` if the Rust crate is treated as a binary application.
6. Keep `execute=false` always.

## Acceptance criteria

- `make validate` passes.
- `make rust-check` passes.
- `make rust-run-fixture` passes and emits a safe boot plan.
- Rust rejects invalid signatures and unknown signers.
- Rust does not download artifacts, write disks, call `kexec`, mutate boot entries, or modify host state.

## Boundary

Do not implement artifact fetching, kexec, disk writes, boot-menu updates, or rollback execution in this task. This is signature/conformance parity only.
