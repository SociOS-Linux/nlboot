from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nlboot.protocol import EnrollmentToken, NlbootError, SignedBootManifest, build_boot_plan


MANIFEST = {
    "manifest_id": "urn:srcos:boot-manifest:m2-demo-recovery",
    "boot_release_set_id": "urn:srcos:boot-release-set:m2-demo-recovery-2026-04-26",
    "base_release_set_ref": "urn:srcos:release-set:m2-demo-2026-04-26",
    "boot_mode": "recovery",
    "artifacts": {
        "kernel_ref": "urn:srcos:artifact:m2-demo-kernel",
        "initrd_ref": "urn:srcos:artifact:m2-demo-initrd",
        "rootfs_ref": "urn:srcos:artifact:m2-demo-rootfs",
    },
    "signature_ref": "urn:srcos:signature:m2-demo-recovery",
    "signer_ref": "urn:srcos:key:sourceos-release-root",
    "signature_algorithm": "rsa-pss-sha256",
    "crypto_profile": "fips-140-3-compatible",
    "signature_hex": "00",
}

TOKEN = {
    "token_id": "urn:srcos:enrollment-token:m2-demo-recovery",
    "purpose": "recovery",
    "audience": {"subject_kind": "device", "subject_id": "urn:srcos:device:m2-local-demo"},
    "release_set_ref": "urn:srcos:release-set:m2-demo-2026-04-26",
    "boot_release_set_ref": "urn:srcos:boot-release-set:m2-demo-recovery-2026-04-26",
    "one_time_use": True,
    "issued_at": "2026-04-26T14:31:00Z",
    "expires_at": "2026-04-26T14:46:00Z",
    "status": "issued",
}


def test_builds_safe_recovery_plan():
    manifest = SignedBootManifest.from_dict(MANIFEST)
    token = EnrollmentToken.from_dict(TOKEN)
    plan = build_boot_plan(manifest, token, now=datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc))
    assert plan.action == "boot-recovery"
    assert plan.execute is False
    assert plan.boot_release_set_id == MANIFEST["boot_release_set_id"]
    assert plan.authorized_by == TOKEN["token_id"]
    assert plan.signature_algorithm == "rsa-pss-sha256"
    assert plan.crypto_profile == "fips-140-3-compatible"


def test_expired_token_rejected():
    manifest = SignedBootManifest.from_dict(MANIFEST)
    token = EnrollmentToken.from_dict(TOKEN)
    with pytest.raises(NlbootError, match="expired"):
        build_boot_plan(manifest, token, now=datetime(2026, 4, 26, 15, 0, tzinfo=timezone.utc))


def test_mismatched_boot_release_set_rejected():
    manifest = SignedBootManifest.from_dict(MANIFEST)
    bad = dict(TOKEN)
    bad["boot_release_set_ref"] = "urn:srcos:boot-release-set:other"
    token = EnrollmentToken.from_dict(bad)
    with pytest.raises(NlbootError, match="boot_release_set_ref"):
        build_boot_plan(manifest, token, now=datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc))


def test_bad_signature_ref_rejected():
    bad = dict(MANIFEST)
    bad["signature_ref"] = "sha256:not-a-signature"
    with pytest.raises(NlbootError, match="signature_ref"):
        SignedBootManifest.from_dict(bad)


def test_wrong_purpose_for_recovery_rejected():
    manifest = SignedBootManifest.from_dict(MANIFEST)
    bad = dict(TOKEN)
    bad["purpose"] = "boot"
    token = EnrollmentToken.from_dict(bad)
    with pytest.raises(NlbootError, match="purpose"):
        build_boot_plan(manifest, token, now=datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc))


def test_non_fips_ready_algorithm_rejected():
    bad = dict(MANIFEST)
    bad["signature_algorithm"] = "ed25519"
    with pytest.raises(NlbootError, match="rsa-pss-sha256"):
        SignedBootManifest.from_dict(bad)


def test_non_fips_ready_profile_rejected():
    bad = dict(MANIFEST)
    bad["crypto_profile"] = "standard"
    with pytest.raises(NlbootError, match="fips-140-3-compatible"):
        SignedBootManifest.from_dict(bad)
