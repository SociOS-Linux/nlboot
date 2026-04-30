# Agent task: gated kexec --exec handoff

Target agent: Codex environment for `SociOS-Linux/nlboot`; Copilot coding agent if available.

## Purpose

NLBoot now has a usable Rust MVP path for:

1. plan;
2. fetch and SHA-256 verify artifacts;
3. write content-addressed cache records;
4. emit evidence;
5. run a dry-run or real `linux-kexec --load-only` path behind explicit host-mutation acknowledgement.

The next useful host-mutation increment is a gated `kexec --exec` handoff.

This task must be implemented cautiously because `kexec --exec` transfers control to the loaded kernel and effectively reboots the host.

## Current state

Current behavior in `rust/nlboot-client/src/main.rs`:

- `execute --adapter linux-kexec --load-only` exists.
- `execute --exec` is refused with: `--exec is not implemented before load-only proof review`.
- `pre-exec-proof.json` is emitted by the load-only path.
- `artifact-cache-record.json` is emitted by the fetch path.

## Required CLI shape

```bash
nlboot-client execute \
  --plan /tmp/nlboot-fixture-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter linux-kexec \
  --exec \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host \
  --i-understand-this-reboots-host
```

Dry-run must also be supported:

```bash
nlboot-client execute \
  --plan /tmp/nlboot-fixture-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter linux-kexec \
  --exec \
  --dry-run \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host \
  --i-understand-this-reboots-host
```

## Scope

1. Add `--i-understand-this-reboots-host` to the `Execute` command.
2. Split execution paths:
   - `--load-only`: existing behavior.
   - `--exec`: new behavior.
3. Require `--i-understand-this-mutates-host` for both paths.
4. Require `--i-understand-this-reboots-host` for `--exec`.
5. Require `pre-exec-proof.json` from a previous load-only phase before allowing `--exec`.
6. Require artifact cache evidence to still verify before `--exec`.
7. Require root or equivalent capability unless `--dry-run` is present.
8. Emit `exec-proof.json` before invoking `kexec --exec`.
9. In dry-run mode, print the proof and do not invoke `kexec`.
10. In real mode, invoke exactly `kexec --exec` after all checks pass.

## Refusal behavior

The client must refuse and write `refusal-record.json` when:

- mutation acknowledgement is missing;
- reboot acknowledgement is missing;
- `pre-exec-proof.json` is missing;
- artifact cache evidence is missing;
- cached artifact hashes no longer match;
- non-root invocation attempts real `--exec`;
- unsupported adapter is requested;
- both `--load-only` and `--exec` are passed together.

## Tests

Add Rust tests for:

- dry-run `--exec` after fixture plan/fetch/load-only dry-run emits `exec-proof.json`;
- missing reboot acknowledgement refuses;
- missing pre-exec proof refuses;
- both `--load-only` and `--exec` together refuse;
- unsupported adapter refuses.

Add Makefile target:

```bash
make rust-exec-dry-run-fixture
```

This target must execute:

1. plan fixture;
2. fetch fixture;
3. execute load-only dry-run;
4. execute exec dry-run;
5. assert `/tmp/nlboot-evidence/exec-proof.json` exists.

## Acceptance criteria

- `make validate` passes.
- `make rust-check` passes.
- `make rust-test` passes.
- `make rust-fetch-fixture` passes.
- `make rust-execute-dry-run-fixture` passes.
- `make rust-exec-dry-run-fixture` passes.
- No real reboot occurs in CI.
- Real `kexec --exec` is only reachable without `--dry-run` and with both explicit acknowledgement flags.

## Boundary

Do not add installer disk writes, Apple Silicon boot entry mutation, rollback execution, or recovery repair execution in this task.

This is only the gated Linux kexec handoff.
