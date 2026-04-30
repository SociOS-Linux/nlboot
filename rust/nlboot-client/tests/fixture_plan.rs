use assert_cmd::Command;
use predicates::prelude::*;

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
        .stdout(predicate::str::contains("RSA-PSS signature verification parity is required"));
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
