# NLBoot dry-run operator quickstart

This quickstart proves the NLBoot operator path without changing the host.

Run these from the repository root.

## Validate reference and Rust clients

```bash
make validate
make rust-check
make rust-test
```

## Prove signed planning

```bash
make rust-run-fixture
```

Expected result: the manifest verifies, the one-time token validates, and the emitted plan keeps `execute=false`.

## Prove artifact fetch, cache, and evidence

```bash
make rust-fetch-fixture
```

Expected evidence:

```text
/tmp/nlboot-evidence/artifact-cache-record.json
```

Expected cache entries include content-addressed kernel, initrd, and rootfs fixture files under `/tmp/nlboot-cache`.

## Prove Linux load-only dry run

```bash
make rust-execute-dry-run-fixture
```

Expected evidence:

```text
/tmp/nlboot-evidence/pre-exec-proof.json
```

## Prove final handoff dry run

```bash
make rust-exec-dry-run-fixture
```

Expected evidence:

```text
/tmp/nlboot-evidence/exec-proof.json
```

## Prove Apple Silicon M2 adapter dry run

```bash
make rust-apple-m2-dry-run-fixture
```

Expected evidence:

```text
/tmp/nlboot-evidence/adapter-plan-record.json
/tmp/nlboot-evidence/boot-entry-record.json
```

The Apple Silicon adapter path is currently evidence-only. It does not change boot entries.

## Evidence checklist

After the full dry-run sequence, inspect:

```text
/tmp/nlboot-evidence/artifact-cache-record.json
/tmp/nlboot-evidence/pre-exec-proof.json
/tmp/nlboot-evidence/exec-proof.json
/tmp/nlboot-evidence/adapter-plan-record.json
/tmp/nlboot-evidence/boot-entry-record.json
```

The dry-run path is healthy when all records exist and reference the same release and boot-release identifiers.

## Refusal expectations

The client should refuse when:

- the signed manifest is invalid;
- the token is expired or mismatched;
- artifact SHA-256 verification fails;
- cache evidence is missing;
- acknowledgement gates are missing;
- final handoff is requested before prior load-only proof;
- the Apple Silicon adapter is asked to operate outside its dry-run proof lane.

## Release-readiness boundary

Dry-run proof is not production readiness. A release candidate also needs passing CI, release archives, SHA-256 sums, provenance attestation, Homebrew tap update path, SourceOS schema integration, SourceOS boot/recovery integration, and a product-shell evidence view.
