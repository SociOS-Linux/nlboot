# NLBoot execution boundary

## Current boundary

NLBoot currently implements safe planning only.

The planner may:

- parse signed boot-manifest-shaped objects;
- verify signature metadata and, in the Python reference path, RSA-PSS/SHA-256 signatures;
- validate enrollment tokens;
- validate boot/release binding;
- select an allowed plan action;
- emit a `BootPlan` JSON object;
- emit `execute=false`.

The planner must not:

- download artifacts;
- mount filesystems;
- write disks;
- update boot entries;
- call `kexec`;
- trigger rollback execution;
- persist enrollment secrets;
- mutate host state.

## Future phases

### Phase 1: planner

Status: active.

Outputs a safe, non-mutating BootPlan.

### Phase 2: fetcher

Status: future.

May fetch artifacts only after:

- signed manifest verification;
- trusted key verification;
- token or device assignment validation;
- policy authorization;
- content hash verification;
- evidence record creation.

Fetcher output must be an artifact cache record, not a host mutation.

### Phase 3: executor

Status: future, separate review required.

May perform privileged operations only after an explicit `execute=true` policy gate and platform adapter approval.

Privileged operations include:

- kexec;
- disk writes;
- boot entry updates;
- rollback execution;
- recovery repair execution;
- installer handoff.

### Phase 4: platform adaptation layer

Status: future.

Platform-specific behavior belongs in adapters, not the portable core.

Initial adapters:

- Apple Silicon / M2 recovery-install entry;
- generic UEFI/iPXE/netboot;
- Purism/Linux-first hardware;
- VM/bootstrap target.

## Refusal rules

NLBoot must refuse to plan, fetch, or execute when any of the following are true:

- manifest signature cannot be verified;
- signer is unknown;
- boot mode is unsupported;
- enrollment token is expired, revoked, redeemed, or not one-time use;
- token release refs do not match manifest refs;
- artifact refs are missing;
- policy does not authorize the requested phase;
- requested platform adapter is unavailable;
- evidence sink is unavailable for a phase that requires evidence.

## M2 stance

M2 is the first-class proof target. It is not the project boundary.

Apple Silicon-specific behavior belongs in the Apple Silicon platform adaptation layer. The portable core must remain valid for other hardware classes.
