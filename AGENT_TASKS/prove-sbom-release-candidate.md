# Agent task: prove SBOM-enabled release-candidate workflow

Target repo: `SociOS-Linux/nlboot`

## Context

The release-candidate workflow has already been proven once through PR #8. After that proof, the workflow and tagged release workflow were hardened to include a deterministic SPDX-style SBOM generated from `cargo metadata` by `tools/cargo_metadata_to_spdx.py`.

The next release-hardening task is to prove the SBOM-enabled release-candidate path.

## Scope

Run the release-candidate workflow after the SBOM wiring changes and verify that the uploaded archive contains:

- `nlboot-client`
- `Cargo.lock`
- `cargo-metadata.json`
- `sbom.spdx.json`
- `release-candidate-manifest.json`
- release/install/readiness docs

## Acceptance criteria

- `.github/workflows/release-candidate.yml` completes successfully.
- Artifact `nlboot-client-release-candidate` is uploaded.
- Archive contains `sbom.spdx.json`.
- Archive contains `cargo-metadata.json`.
- Archive SHA-256 file is produced.
- Provenance attestation step succeeds where GitHub supports it.
- Any failure is documented with the exact failing step and next patch.

## Suggested manual trigger

```bash
gh workflow run "nlboot release candidate" \
  -R SociOS-Linux/nlboot \
  --ref main
```

Then inspect:

```bash
gh run list -R SociOS-Linux/nlboot --workflow "nlboot release candidate" --limit 3
gh run view -R SociOS-Linux/nlboot <RUN_ID> --log-failed
gh run download -R SociOS-Linux/nlboot <RUN_ID> -n nlboot-client-release-candidate
```

## Boundary

Do not publish a tagged GitHub release in this task.

Do not create or update a Homebrew formula in this task.

Do not change boot, recovery, handoff, installer, or host behavior.
