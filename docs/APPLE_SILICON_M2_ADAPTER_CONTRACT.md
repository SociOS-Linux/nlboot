# Apple Silicon M2 adapter contract

This contract defines the first usable SourceOS adapter target for Apple Silicon M2 machines.

The M2 adapter is a platform adaptation layer. It must consume the portable NLBoot plan and evidence model without moving Apple-specific behavior into the portable core.

## Contract scope

The adapter is responsible for representing and eventually managing two SourceOS-visible entries:

1. `SourceOS`
2. `SourceOS Recovery/Installer`

The current contract is dry-run only. It emits records that describe what would be presented and which release references are attached. It must not change host boot configuration in the dry-run stage.

## Inputs

The adapter consumes:

- a verified `BootPlan`;
- a verified `BootReleaseSet` reference;
- a `ReleaseSet` reference;
- trusted key and manifest verification evidence;
- a policy decision allowing the adapter action;
- an evidence directory.

## Outputs

The dry-run adapter must emit:

- `adapter-plan-record.json`;
- `boot-entry-record.json`;
- `refusal-record.json` on block.

The records must include:

- adapter name;
- mode;
- dry-run flag;
- mutation-performed flag;
- boot release set ID;
- release set ref;
- proposed visible entries;
- required follow-up proofs.

## Refusal rules

The adapter must refuse when:

- no verified plan is available;
- the plan is not bound to a signed manifest;
- policy does not allow the requested adapter action;
- evidence output cannot be written;
- the request attempts non-dry-run behavior before the reviewed implementation exists;
- target platform does not match the Apple Silicon adapter.

## Dry-run fixture

The repository carries a dry-run fixture at:

`examples/apple_silicon_m2_adapter_plan.recovery.json`

This fixture is not an executable host change. It is the expected adapter evidence shape for the first implementation pass.

## Maturity gates

### M3

- Contract exists.
- Fixture validates as JSON.
- Adapter dry-run command emits records matching fixture shape.
- No host mutation occurs.

### M4

- Recovery/Installer entry can be generated as a build artifact.
- Recovery environment can fetch and verify NLBoot artifacts.
- Rollback selection is represented in dry-run evidence.

### M5

- M2 can present SourceOS and SourceOS Recovery/Installer entries.
- Recovery path can perform verified repair, update, or rollback with evidence.
- Post-action fingerprint is visible to the control plane.
