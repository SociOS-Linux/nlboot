# Agent task: usable NLBoot MVP with fetch/cache and kexec load-only path

Target agent: Codex environment for `SociOS-Linux/nlboot`; Copilot coding agent if available.

## Purpose

The current NLBoot implementation proves safe planning. That is not enough for usable boot/recovery work.

This task adds the first usable MVP lane while preserving safety:

1. plan;
2. fetch verified artifacts into cache;
3. emit evidence;
4. prepare a Linux kexec load-only handoff behind explicit host-mutation gates.

## Required CLI shape

```bash
nlboot-client plan \
  --manifest examples/signed_boot_manifest.recovery.json \
  --token examples/enrollment_token.recovery.json \
  --trusted-keys examples/trusted_keys.recovery.json \
  --require-fips \
  --now 2026-04-26T14:35:00Z \
  --out /tmp/nlboot-plan.json

nlboot-client fetch \
  --plan /tmp/nlboot-plan.json \
  --artifact-map examples/artifact_map.recovery.json \
  --cache /tmp/nlboot-cache \
  --evidence /tmp/nlboot-evidence

nlboot-client execute \
  --plan /tmp/nlboot-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter linux-kexec \
  --load-only \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host
```

`--exec` must not be implemented before `--load-only` is proven and reviewed.

## Scope

### Plan

- Add `--out` to write the plan to disk.
- Preserve stdout JSON behavior when `--out` is omitted.
- Keep `execute=false` in the plan.

### Artifact map

Add an example `examples/artifact_map.recovery.json` mapping artifact refs to local fixture paths or HTTPS URLs.

Each artifact entry must include:

- `artifact_ref`;
- `source`;
- `sha256`;
- `size_bytes` when known;
- `kind`: `kernel`, `initrd`, or `rootfs`;
- `content_type`.

### Fetch/cache

Implement `nlboot-client fetch`:

- read a previously generated plan;
- resolve artifact refs through an artifact map;
- fetch or copy artifacts;
- compute SHA-256;
- refuse hash mismatch;
- write artifacts into cache under content-addressed names;
- emit `artifact-cache-record.json` into the evidence directory;
- perform no kexec, disk write, or boot entry mutation.

### Execute load-only

Implement `nlboot-client execute --adapter linux-kexec --load-only`:

- refuse unless `--i-understand-this-mutates-host` is present;
- refuse unless artifacts are present in cache and hashes match evidence;
- refuse unless process is root or can show the required capability;
- construct but do not hide the kexec command;
- execute `kexec --load` only in `--load-only` mode;
- emit `pre-exec-proof.json` before invoking kexec;
- never call `kexec --exec` in this task.

### Evidence

Emit evidence records:

- `plan-record.json`;
- `artifact-cache-record.json`;
- `pre-exec-proof.json`;
- `refusal-record.json` on any refusal.

## Acceptance criteria

- `make validate` passes.
- `make rust-check` passes.
- `make rust-test` passes.
- `make rust-run-fixture` passes.
- A new `make rust-fetch-fixture` passes using local fixture artifacts.
- `execute --load-only` refuses without the explicit host-mutation flag.
- `execute --load-only` refuses when not root or missing required capability.
- `execute --load-only` never calls `kexec --exec`.
- All host mutation behavior is documented in `docs/EXECUTION_BOUNDARY.md`.

## Boundary

Do not implement installer disk writes, rollback execution, Apple Silicon boot entry mutation, or `kexec --exec` in this task.

This task is useful MVP, not full production recovery.
