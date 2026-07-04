# NLBoot lifecycle contracts

NLBoot now carries the contract layer that connects the executable boot/recovery client to the SourceOS control plane.

The Rust client already proves signed manifest validation, token validation, artifact fetch/cache, evidence output, gated Linux kexec dry-run, and Apple Silicon M2 adapter dry-run. The lifecycle contracts define the higher-level objects that the website/control plane must build, sign, assign, and verify.

## Contract objects

| Object | Schema | Purpose |
|---|---|---|
| `ReleaseSet` | `schemas/release-set.schema.v0.1.json` | Signed SourceOS lifecycle release binding system target, user closures, agent closures, policy, BOM, rollback, and evidence. |
| `BootReleaseSet` | `schemas/boot-release-set.schema.v0.1.json` | Bootable/recovery release binding `ReleaseSet` to signed boot manifest, boot artifacts, platform adapters, authorization, offline fallback, signing, and proof requirements. |
| `LifecycleStateRecord` | `schemas/lifecycle-state-record.schema.v0.1.json` | Control-plane transition record for build/sign/assign/plan/fetch/load/execute/attest/compliance/rollback states. |

Examples:

```text
examples/release_set.m2_demo.json
examples/boot_release_set.m2_demo_recovery.json
examples/lifecycle_state_record.m2_demo_signed.json
```

Validation:

```bash
make validate-lifecycle-contracts
make validate
```

## State design

The lifecycle path is intentionally explicit:

```text
DraftProfile
  -> ResolvedBOM
  -> Built
  -> Signed
  -> Assigned
  -> Planned
  -> Fetched
  -> Loaded
  -> Executed
  -> Attested
  -> Compliant / Noncompliant
  -> RollbackAvailable
  -> RolledBack
```

Each transition emits or references a `LifecycleStateRecord`.

## BootReleaseSet and NLBoot

`BootReleaseSet` does not replace `SignedBootManifest` or `BootPlan`.

It binds them to the SourceOS control-plane lifecycle:

```text
ReleaseSet
  -> BootReleaseSet
  -> SignedBootManifest
  -> EnrollmentToken
  -> BootPlan
  -> fetch/cache evidence
  -> adapter evidence
  -> fingerprint/compliance/rollback evidence
```

## M2 proof target

The Apple Silicon M2 path remains first-class but not exclusive.

`BootReleaseSet` supports platform adapters including:

- `apple-silicon-m2`
- `linux-kexec`
- `uefi-ipxe`
- `purism-linux`
- `vm-bootstrap`

The M2 adapter remains dry-run only until reviewed platform-specific host mutation exists. The contract requires evidence for proposed visible entries:

```text
SourceOS
SourceOS Recovery/Installer
```

## Safety invariants

- Unsigned fallback is forbidden.
- One-time enrollment token is required for boot/recovery authorization.
- Device claim is required.
- Last-known-good fallback is required for recovery posture.
- Host mutation is explicit and evidence-backed.
- Reboot paths require explicit acknowledgement in executor paths.
- Signing records do not mutate host state.
- Boot/recovery action must emit plan, fetch, adapter, and fingerprint evidence.

## Website/control-plane responsibility

The website/control plane must eventually own:

- profile selection;
- BOM resolution;
- ReleaseSet creation and signing;
- BootReleaseSet creation and signing;
- enrollment token issuance;
- device assignment;
- lifecycle transition records;
- artifact hosting;
- compliance dashboard;
- rollback assignment.

NLBoot owns portable boot planning, artifact fetch/cache/evidence, and platform adapter execution boundaries.
