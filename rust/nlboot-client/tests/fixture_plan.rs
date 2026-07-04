use assert_cmd::Command;
use predicates::prelude::*;
use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use tempfile::tempdir;

fn write_plan(path: &Path) {
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
            path.to_str().unwrap(),
        ])
        .assert()
        .success();
}

fn fetch_fixture(plan_path: &Path, cache_dir: &Path, evidence_dir: &Path) {
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
}

fn load_only_dry_run(plan_path: &Path, cache_dir: &Path, evidence_dir: &Path) {
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
        .success();
}

fn prepared_fixture() -> (tempfile::TempDir, PathBuf, PathBuf, PathBuf) {
    let dir = tempdir().expect("tempdir");
    let plan_path = dir.path().join("plan.json");
    let cache_dir = dir.path().join("cache");
    let evidence_dir = dir.path().join("evidence");
    write_plan(&plan_path);
    fetch_fixture(&plan_path, &cache_dir, &evidence_dir);
    (dir, plan_path, cache_dir, evidence_dir)
}

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

    write_plan(&plan_path);
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
fn execute_load_only_dry_run_emits_pre_exec_proof() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();

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
fn execute_exec_dry_run_requires_prior_load_only_and_emits_exec_proof() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();
    load_only_dry_run(&plan_path, &cache_dir, &evidence_dir);

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
            "--exec",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
            "--i-understand-this-reboots-host",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("\"kind\": \"exec-proof\""))
        .stdout(predicate::str::contains("\"dry_run\": true"))
        .stdout(predicate::str::contains("\"execute_exec\": true"));

    assert!(evidence_dir.join("exec-proof.json").exists());
}

#[test]
fn apple_silicon_m2_dry_run_emits_adapter_records() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "execute",
            "--plan",
            plan_path.to_str().unwrap(),
            "--cache",
            cache_dir.to_str().unwrap(),
            "--adapter",
            "apple-silicon-m2",
            "--load-only",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
        ])
        .assert()
        .success()
        .stdout(predicate::str::contains("\"kind\": \"adapter-plan-record\""))
        .stdout(predicate::str::contains("\"adapter\": \"apple-silicon-m2\""))
        .stdout(predicate::str::contains("\"dry_run\": true"));

    assert!(evidence_dir.join("adapter-plan-record.json").exists());
    assert!(evidence_dir.join("boot-entry-record.json").exists());
    let raw = fs::read_to_string(evidence_dir.join("boot-entry-record.json")).expect("read entry record");
    assert!(raw.contains("SourceOS"));
    assert!(raw.contains("SourceOS Recovery/Installer"));
}

#[test]
fn apple_silicon_m2_refuses_without_acknowledgement() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "execute",
            "--plan",
            plan_path.to_str().unwrap(),
            "--cache",
            cache_dir.to_str().unwrap(),
            "--adapter",
            "apple-silicon-m2",
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
fn apple_silicon_m2_refuses_non_dry_run() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();

    Command::cargo_bin("nlboot-client")
        .expect("nlboot-client binary exists")
        .args([
            "execute",
            "--plan",
            plan_path.to_str().unwrap(),
            "--cache",
            cache_dir.to_str().unwrap(),
            "--adapter",
            "apple-silicon-m2",
            "--load-only",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("m2 adapter proof currently requires dry-run mode"));

    assert!(evidence_dir.join("refusal-record.json").exists());
}

#[test]
fn execute_refuses_without_mutation_acknowledgement() {
    let dir = tempdir().expect("tempdir");
    let plan_path = dir.path().join("plan.json");
    let cache_dir = dir.path().join("cache");
    let evidence_dir = dir.path().join("evidence");

    write_plan(&plan_path);

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
fn execute_exec_refuses_without_reboot_acknowledgement() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();
    load_only_dry_run(&plan_path, &cache_dir, &evidence_dir);

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
            "--exec",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("refusing kexec --exec without --i-understand-this-reboots-host"));

    assert!(evidence_dir.join("refusal-record.json").exists());
}

#[test]
fn execute_exec_refuses_without_prior_load_only_proof() {
    let (_dir, plan_path, cache_dir, evidence_dir) = prepared_fixture();

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
            "--exec",
            "--dry-run",
            "--evidence",
            evidence_dir.to_str().unwrap(),
            "--i-understand-this-mutates-host",
            "--i-understand-this-reboots-host",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("missing pre-exec-proof.json from prior load-only phase"));

    assert!(evidence_dir.join("refusal-record.json").exists());
}

#[test]
fn execute_refuses_both_load_only_and_exec() {
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
            "--i-understand-this-reboots-host",
        ])
        .assert()
        .failure()
        .stderr(predicate::str::contains("choose either --load-only or --exec, not both"));

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
