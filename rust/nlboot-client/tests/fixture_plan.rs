use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use std::fs;
use tempfile::tempdir;

#[test]
fn emits_execute_false_plan_for_m2_recovery_fixture() {
    let mut cmd = Command::cargo_bin("nlboot-client").expect("nlboot-client binary exists");
    cmd.args([
        "plan",
        "--manifest",
        "../../examples/signed_boot_manifest.recovery.json",
        "--token",
        "../../examples/enrollment_token.recovery.json",
        "--trusted-keys",
        "../../examples/trusted_keys.recovery.json",
        "--require-fips",
        "--now",
        "2026-04-26T14:35:00Z",
    ]);

    cmd.assert()
        .success()
        .stdout(predicate::str::contains("\"ok\": true"))
        .stdout(predicate::str::contains("\"action\": \"boot-recovery\""))
        .stdout(predicate::str::contains("\"execute\": false"))
        .stdout(predicate::str::contains("Rust planner verifies RSA-PSS/SHA-256 manifest signatures"));
}

#[test]
fn rejects_expired_token_for_m2_recovery_fixture() {
    let mut cmd = Command::cargo_bin("nlboot-client").expect("nlboot-client binary exists");
    cmd.args([
        "plan",
        "--manifest",
        "../../examples/signed_boot_manifest.recovery.json",
        "--token",
        "../../examples/enrollment_token.recovery.json",
        "--trusted-keys",
        "../../examples/trusted_keys.recovery.json",
        "--require-fips",
        "--now",
        "2026-04-26T15:00:00Z",
    ]);

    cmd.assert()
        .failure()
        .stderr(predicate::str::contains("token is expired"));
}

#[test]
fn rejects_tampered_manifest_signature() {
    let dir = tempdir().expect("tempdir");
    let tampered_manifest_path = dir.path().join("tampered-manifest.json");
    let raw = fs::read_to_string("../../examples/signed_boot_manifest.recovery.json").expect("read fixture manifest");
    let mut manifest: Value = serde_json::from_str(&raw).expect("parse fixture manifest");
    manifest["signature_hex"] = Value::String("00".repeat(256));
    fs::write(
        &tampered_manifest_path,
        serde_json::to_string_pretty(&manifest).expect("serialize tampered manifest"),
    )
    .expect("write tampered manifest");

    let mut cmd = Command::cargo_bin("nlboot-client").expect("nlboot-client binary exists");
    cmd.args([
        "plan",
        "--manifest",
        tampered_manifest_path.to_str().expect("manifest path"),
        "--token",
        "../../examples/enrollment_token.recovery.json",
        "--trusted-keys",
        "../../examples/trusted_keys.recovery.json",
        "--require-fips",
        "--now",
        "2026-04-26T14:35:00Z",
    ]);

    cmd.assert()
        .failure()
        .stderr(predicate::str::contains("signature verification failed"));
}
