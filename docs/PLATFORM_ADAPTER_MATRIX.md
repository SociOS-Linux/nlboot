# NLBoot platform adapter matrix

NLBoot is a portable boot and recovery planning protocol with platform-specific adaptation layers.

M2 is the first-class proof target. It is not the project boundary.

## Portable core

The portable core must remain platform-neutral:

- signed boot manifest / BootReleaseSet validation;
- trusted key handling;
- enrollment token validation;
- device claim binding;
- boot mode to plan-action mapping;
- proof requirement selection;
- offline fallback policy;
- refusal behavior;
- BootPlan and BootProof output.

The portable core must not encode Apple Silicon, UEFI, Purism, or VM-specific assumptions.

## Platform adapters

| Adapter | Priority | Purpose | Status | Required proof |
| --- | --- | --- | --- | --- |
| Apple Silicon / M2 | P0 | First hardware proof target; SourceOS recovery/install entry; boot picker parity; M2 local demo. | planned | M2 recovery fixture, SourceOS Recovery entry plan, rollback plan, device claim proof. |
| Generic UEFI / iPXE | P1 | Secure PXE-like network boot/install/recovery for commodity PCs and fleet-like provisioning. | planned | iPXE/UEFI boot channel manifest, HTTPS/mTLS posture, signed artifact plan, refusal tests. |
| Purism / Linux-first hardware | P1 | Linux-native hardware control group that avoids Apple-specific assumptions. | planned | disk layout plan, secure boot posture note, recovery/rollback proof. |
| VM / bootstrap target | P1 | Dev/test target for local control-plane proof, CI smoke tests, and non-destructive demos. | planned | ephemeral boot plan, no-disk-write guarantee, fixture smoke. |
| Container-only simulation | P2 | Protocol and planner simulation only. Not a real boot target. | reference only | parser/conformance tests. |

## Apple Silicon / M2 adapter

The M2 adapter should provide capability parity with a recovery-style boot flow without pretending to run inside Apple recoveryOS.

Responsibilities:

- represent SourceOS normal and SourceOS Recovery/Installer entries;
- map BootReleaseSet channels to Apple Silicon-compatible boot/install entry semantics;
- support local network enrollment and one-time code entry;
- fetch only authorized signed artifacts in future fetcher phase;
- expose rollback/recovery plan choices;
- emit device claim and post-action fingerprint evidence.

Non-goals:

- no Apple recoveryOS replacement claim;
- no host mutation in the portable planner;
- no M2 assumptions in the portable core.

## Generic UEFI / iPXE adapter

The UEFI/iPXE adapter should provide secure PXE-like semantics.

Responsibilities:

- support live/install/rescue/rollback channel menus;
- use signed manifests and trusted keys;
- prefer HTTPS and mTLS where feasible;
- reject unsigned artifacts;
- bind boot instructions to device assignment or one-time enrollment.

## Purism / Linux-first adapter

The Purism/Linux-first adapter is the control-group implementation for Linux-native hardware.

Responsibilities:

- validate that the portable core works without Apple Silicon assumptions;
- document secure boot and firmware posture;
- prove recovery/rollback on a conventional Linux-first machine.

## VM/bootstrap adapter

The VM/bootstrap adapter exists to keep development and CI fast.

Responsibilities:

- exercise the BootReleaseSet protocol without touching real disks;
- support local control-plane demos;
- prove planner/fetcher behavior before hardware execution.

## Adapter readiness gates

An adapter is not considered ready until it has:

1. a fixture;
2. a documented boot channel mapping;
3. refusal tests;
4. evidence output;
5. compatibility notes;
6. no-host-mutation proof for planning-only mode;
7. explicit execution-gate policy for any future host mutation.
