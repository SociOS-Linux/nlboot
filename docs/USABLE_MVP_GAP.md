# NLBoot usable MVP gap

NLBoot is currently safe, but not yet useful enough for real boot/recovery work.

The current planner proves trust and intent. The usable MVP must add controlled host mutation.

## Current state

Implemented now:

- signed boot-manifest parsing;
- RSA-PSS/SHA-256 manifest verification in the Python reference planner;
- Rust production-client lane with signature-verification work in progress;
- one-time enrollment token validation;
- safe `BootPlan` emission;
- M2 recovery fixture;
- `execute=false` default;
- no host mutation.

This is M2/M3 reference maturity, not a usable boot system.

## Missing for use

### 1. Rust verification parity must be green

The Rust client must pass:

```bash
make rust-check
make rust-test
make rust-run-fixture
```

Rust must verify the same signed manifest fixture as Python and reject tampered signatures.

### 2. Artifact refs need fetch semantics

The manifest currently carries artifact refs. A usable client needs explicit artifact records:

- URL or local path;
- expected SHA-256 digest;
- size;
- content type;
- cache key;
- required trust root;
- optional mirror list.

Fetcher mode must:

- fetch kernel/initrd/rootfs artifacts;
- verify SHA-256 before use;
- write only to an NLBoot cache directory;
- emit an artifact cache record;
- never execute anything by default.

### 3. Last-known-good cache

Recovery requires a last-known-good cache:

- previous verified BootReleaseSet;
- previous verified artifact set;
- previous proof record;
- refusal reason if fallback is unavailable.

The fallback cache must reject unsigned or hash-mismatched artifacts.

### 4. Host mutation gate

Host mutation must be explicit.

Required flags for any mutation path:

```bash
nlboot-client execute --plan plan.json --i-understand-this-mutates-host --adapter <adapter>
```

Required preconditions:

- signed manifest verified;
- trusted key active;
- token or device assignment valid;
- artifact hashes verified;
- policy authorizes execution phase;
- adapter supports requested operation;
- evidence sink available;
- process has required privileges;
- dry-run output has been shown or recorded.

### 5. Kexec executor

For Linux/Purism/VM targets, the first executor should be kexec handoff.

Required behavior:

- require explicit execute mode;
- require root or required capability;
- invoke `kexec --load` with verified kernel/initrd/args;
- never use unverified paths;
- emit pre-exec proof;
- optionally require a second confirmation flag before `kexec --exec`.

Initial implementation should support two-stage execution:

```bash
nlboot-client fetch --plan plan.json --cache /var/lib/nlboot/cache
nlboot-client execute --plan plan.json --adapter linux-kexec --load-only
nlboot-client execute --plan plan.json --adapter linux-kexec --exec --i-understand-this-mutates-host
```

### 6. Apple Silicon / M2 adapter

M2 remains first-class but not exclusive.

M2 usable proof requires:

- SourceOS Recovery/Installer entry plan;
- integration notes for Asahi-compatible boot entry packaging;
- artifact fetch and verification in the recovery environment;
- rollback menu semantics;
- proof emission back to the control plane.

M2 execution must live in the Apple Silicon platform adapter, not the portable core.

### 7. Generic UEFI / Purism adapter

The second proof target should be a generic Linux-first machine or VM.

This path should use:

- secure netboot or bootstrap media semantics;
- verified kernel/initrd/rootfs artifacts;
- kexec handoff or installer handoff;
- same BootReleaseSet and token model as M2.

### 8. Evidence output

Every phase must emit evidence:

- plan record;
- fetch record;
- verification record;
- cache record;
- pre-exec proof;
- post-action fingerprint where possible;
- refusal record when blocked.

## Usable MVP command target

The first usable MVP should support:

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
  --cache /var/lib/nlboot/cache \
  --evidence /var/lib/nlboot/evidence

nlboot-client execute \
  --plan /tmp/nlboot-plan.json \
  --adapter linux-kexec \
  --load-only \
  --evidence /var/lib/nlboot/evidence
```

Only after that should `--exec` exist.

## Maturity target

- M3: Rust/Python verification parity, negative tests, plan/fetch contract.
- M4: signed release artifacts and usable fetch/cache/load-only kexec executor.
- M5: M2 recovery proof plus second platform proof with rollback/evidence.
