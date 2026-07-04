# Agent task: evolve NLBoot toward SourceOS BootReleaseSet integration

Target agent: Codex environment for `SociOS-Linux/nlboot`; Copilot coding agent if available through repository settings.

## Current repo state

NLBoot is already a conservative SourceOS network/live/recovery boot protocol reference implementation. It validates signed-boot-manifest-shaped objects, verifies RSA-PSS/SHA-256 manifest signatures, validates one-time enrollment tokens, produces safe `execute=false` boot plans, and carries M2 recovery fixtures.

This repository should remain conservative until verified artifact fetching, kexec, disk writes, and host mutation gates are fully specified and reviewed.

## Scope

1. Inspect the live repository before editing.
2. Align terminology with SourceOS contracts:
   - `BootInstructions` -> `BootReleaseSet`
   - claim code/client cert -> `EnrollmentToken` + `DeviceClaim`
   - fallback config -> last-known-good `BootReleaseSet`
   - planner result -> `BootPlan` + `BootProof`
3. Add or harden `boot-proof.v1` fixture coverage.
4. Add negative tests for invalid signature, expired token, mismatched release refs, mismatched boot-release refs, and unsupported boot mode.
5. Keep checksum/signature examples at SHA-256 / RSA-PSS or stronger. Do not add SHA-1 examples.
6. Document Mac/Apple Silicon behavior as platform-adaptation guidance, not as generic PXE behavior.
7. Add `repo.maturity.yaml` validation to `make validate` if not already wired.

## Acceptance criteria

- `make validate` passes.
- README/docs clearly state what is implemented versus design-only.
- No host mutation path is introduced without explicit `execute=true` policy gates and separate review.
- M2 recovery fixture remains side-effect-free.
- The repo remains compatible with `SourceOS-Linux/sourceos-spec` as the normative schema home.

## Boundary

One PR only. Do not implement full installer behavior here. Do not commit boot keys, private tokens, credentials, binary images, or secrets.
