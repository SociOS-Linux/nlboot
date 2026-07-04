# SBOM release-candidate proof

This PR exists to trigger the SBOM-enabled NLBoot release-candidate workflow through the normal pull-request path.

Expected artifact contents after the workflow succeeds:

- `nlboot-client`
- `Cargo.lock`
- `cargo-metadata.json`
- `sbom.spdx.json`
- `release-candidate-manifest.json`
- release and readiness documentation

This proof does not publish a stable release and does not change runtime or host behavior.
