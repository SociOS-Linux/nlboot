# Agent task: Apple Silicon M2 adapter dry-run proof

Target agent: Codex environment for `SociOS-Linux/nlboot`; Copilot coding agent if available.

## Purpose

The Linux/Purism/VM path now has a usable Rust MVP chain. The M2 proof target needs a platform adapter dry-run lane that represents SourceOS normal and SourceOS Recovery/Installer entries without changing host boot configuration.

## Required behavior

Add support for:

```bash
nlboot-client execute \
  --plan /tmp/nlboot-fixture-plan.json \
  --cache /tmp/nlboot-cache \
  --adapter apple-silicon-m2 \
  --load-only \
  --dry-run \
  --evidence /tmp/nlboot-evidence \
  --i-understand-this-mutates-host
```

This command must:

1. read the verified plan;
2. require dry-run mode;
3. require explicit mutation acknowledgement, even though dry-run performs no mutation;
4. emit `adapter-plan-record.json`;
5. emit `boot-entry-record.json`;
6. refuse any non-dry-run M2 adapter operation;
7. refuse `--exec` for the M2 adapter until the real platform adapter is reviewed;
8. never invoke host boot tooling in this task.

## Fixture

Use this fixture as the expected shape:

`examples/apple_silicon_m2_adapter_plan.recovery.json`

The exact timestamps may differ. The semantic fields must match.

## Tests

Add Rust tests for:

- M2 adapter dry-run emits adapter and boot-entry evidence;
- M2 adapter refuses without mutation acknowledgement;
- M2 adapter refuses without `--dry-run`;
- M2 adapter refuses `--exec`;
- unsupported adapter still refuses.

## Makefile target

Add:

```bash
make rust-apple-m2-dry-run-fixture
```

This target must:

1. run the fixture plan;
2. run fetch/cache;
3. run M2 adapter dry-run;
4. assert `/tmp/nlboot-evidence/adapter-plan-record.json` exists;
5. assert `/tmp/nlboot-evidence/boot-entry-record.json` exists.

## Acceptance criteria

- `make validate` passes.
- `make rust-check` passes.
- `make rust-test` passes.
- `make rust-exec-dry-run-fixture` passes.
- `make rust-apple-m2-dry-run-fixture` passes.
- CI runs the M2 dry-run fixture without mutating host state.

## Boundary

Do not implement real Apple Silicon boot entry mutation in this task.

Do not claim the adapter installs SourceOS yet.

This task is evidence-only dry-run proof for the M2 adapter surface.
