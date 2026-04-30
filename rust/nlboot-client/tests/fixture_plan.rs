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
fn writes_plan_fetches_artifacts_and_emits_evidence() {
    let dir = tempdir().expect("tempdir");
    let plan_path = dir.path().join("plan.json");
    let cache_dir = dir.path().join("cache");
    let evidence_dir = dir.path().join("evidence");

    let mut plan_cmd = Command::cargo_bin("nlboot-client").expect("nlboot-client binary exists");
    plan_cmd.args([
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
        "--out",
        plan_path.to_str().unwrap(),
    ]);
    plan_cmd.assert().success();
    assert!(plan_path.exists(), "plan output should be written");

    let mut fetch_cmd = Command::cargo_bin("nlboot-client").expect("nlboot-client binary exists");
    fetch_cmd.args([
        "fetch",
        "--plan",
        plan_path.to_str().unwrap(),
        "--artifact-map",
        "../../examples/artifact_map.recovery.json",
        "--cache",
        cache_dir.to_str().unwrap(),
        "--evidence",
        evidence_dir.to_str().unwrap(),
    ]);
    fetch_cmd
        .assert()
        .success()
        .stdout(predicate::str::contains("\"ok\": true"))
        .stdout(predicate::str::contains("artifact-map:m2-demo-recovery"));

    let cache_record = evidence_dir.join("artifact-cache-record.json");
    assert!(cache_record.exists(), "artifact cache evidence should be written");
    let raw = fs::read_to_string(cache_record).expect("read cache record");
    assert!(raw.contains("m2-demo-recovery-kernel"));
    assert!(raw.contains("m2-demo-recovery-initrd"));
    assert!(raw.contains("m2-demo-recovery-rootfs"));
}

#[test]
fn execute_dry_run_emits_pre_exec_proof() {
    let dir = tempdir().expect("tempdir");
    let plan_path = dir.path().join("plan.json");
    let cache_dir = dir.path().join("cache");
    let evidence_dir = dir.path().join("evidence");

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
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
            "--out",
            plan_path.to_str().unwrap(),
        ])
        .assert()
        .success();

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "fetch",
            "--plan",
            plan_path.to_str().unwrap(),
            "--artifact-map",
            "../../examples/artifact_map.recovery.json",
            "--cache",
            cache_dir.to_str().unwrap(),
            "--evidence",
            evidence_dir.to_str().unwrap(),
        ])
        .assert()
        .success();

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "execute",
            "--plan",
            plan_path.to_str().unwrap(),
            "--cache",
            cache_dir.to_str().unwrap(),
            "--adapter",
            "linux-kexec",
            "--load-only",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("\"kind\": \"pre-exec-proof\""))
        .stdout(predicate::str::contains("\"dry_run\": true"))
        .stdout(predicate::str::contains("\"execute_exec\": false"));

    assert!(evidence_dir.join("pre-exec-proof.json").exists());
}

#[test]
fn execute_refuses_without_mutation_acknowledgement() {
    let dir = tempdir().expect("tempdir");
    let plan_path = dir.path().join("plan.json");
    let cache_dir = dir.path().join("cache");
    let evidence_dir = dir.path().join("evidence");

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
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
            "--out",
            plan_path.to_str().unwrap(),
        ])
        .assert()
        .success();

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "execute",
            "--plan",
            plan_path.to_str().unwrap(),
            "--cache",
            cache_dir.to_str().unwrap(),
            "--adapter",
            "linux-kexec",
            "--load-only",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("refusing host mutation without --i-understand-this-mutates-host"));

    assert!(evidence_dir.join("refusal-record.json").exists());
}

#[test]
fn execute_refuses_exec_mode_until_reviewed() {
    let dir = tempdir().expect("tempdir");
    let evidence_dir = dir.path().join("evidence");

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "execute",
            "--plan",
            "missing-plan.json",
            "--cache",
            "missing-cache",
            "--adapter",
            "linux-kexec",
            "--load-only",
            "--exec",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("--exec is not implemented before load-only proof review"));

    assert!(evidence_dir.join("refusal-record.json").exists());
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
