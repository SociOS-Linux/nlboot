# Apple Silicon / M2 adapter plan

M2 is the first-class proof target for SourceOS. It is not the boundary of NLBoot, but it is the target that must work first on real hardware.

NLBoot's portable core must not become Apple-specific. Apple Silicon behavior belongs in a platform adapter.

## Goal

Provide SourceOS boot/recovery capability comparable to the macOS user experience:

- normal SourceOS boot entry;
- SourceOS Recovery/Installer boot entry;
- version/rollback choices;
- network enrollment and artifact fetch;
- signed BootReleaseSet verification;
- repair/re-pin user and agent closures;
- evidence emission to the local/control-plane site.

## Constraints

Apple Silicon does not behave like commodity BIOS/UEFI PXE.

The adapter must respect Apple Silicon boot realities and borrow proven mechanics from the Asahi ecosystem where appropriate.

The adapter must not claim to replace Apple recoveryOS or run arbitrary code inside Apple's signed 1TR recovery environment.

## Adapter responsibilities

### 1. Boot entry packaging

The adapter must define how SourceOS normal and SourceOS Recovery/Installer entries are packaged so they appear as selectable boot options on the M2.

Outputs:

- boot entry metadata;
- installer/recovery entry metadata;
- artifact references;
- rollback entry references;
- user-visible labels.

### 2. Recovery environment

The SourceOS Recovery Environment should be minimal and immutable.

Required components:

- `nlboot-client`;
- network setup;
- trusted key material or trust-root refs;
- one-time enrollment code entry;
- BootReleaseSet fetch/verify;
- ReleaseSet fetch/verify;
- evidence upload or local evidence persistence;
- rollback menu / selection surface.

### 3. Artifact verification

Before any install, repair, or rollback action, the adapter must verify:

- signed BootReleaseSet manifest;
- trusted key status;
- artifact SHA-256;
- policy authorization;
- target hardware/platform compatibility.

### 4. Rollback semantics

The adapter must expose rollback as a first-class recovery action.

Rollback targets are not arbitrary images. They are prior verified ReleaseSet or BootReleaseSet records.

### 5. Evidence

The adapter must emit:

- adapter-plan-record.json;
- boot-entry-record.json;
- fetch-record.json;
- verification-record.json;
- pre-mutation-proof.json;
- post-action-fingerprint.json where possible;
- refusal-record.json on any refusal.

## Refusal rules

The adapter must refuse when:

- platform is not Apple Silicon / target hardware does not match;
- trusted key is missing or inactive;
- manifest signature fails;
- artifact hash fails;
- BootReleaseSet is not assigned to the device or entered one-time token;
- requested operation would mutate disk without explicit policy authorization;
- evidence sink is unavailable for required mutation phases.

## Relationship to linux-kexec adapter

`linux-kexec` is the first generic Linux/Purism/VM executor path.

The Apple Silicon adapter is separate. It may use Linux mechanisms inside the recovery environment, but boot-entry creation, installer handoff, and rollback semantics are Apple Silicon-specific.

## Maturity gates

### M3

- Adapter contract documented.
- Fixture BootReleaseSet exists.
- Dry-run adapter plan emits evidence.

### M4

- SourceOS Recovery/Installer entry can be produced as a build artifact.
- Recovery environment can fetch and verify BootReleaseSet/ReleaseSet artifacts.
- Rollback menu semantics are testable in dry-run.

### M5

- The M2 can boot SourceOS and SourceOS Recovery/Installer as selectable entries.
- Recovery can apply a verified repair/update/rollback path.
- Post-action evidence is emitted and visible in the control plane.

## Immediate next task

Create an `AGENT_TASKS/apple-silicon-adapter-dry-run.md` task packet that adds an adapter dry-run fixture and evidence output without mutating the host.
