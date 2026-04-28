from __future__ import annotations

from copy import deepcopy
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


def manifest_with_boot_menu() -> dict[str, object]:
    manifest = deepcopy(MANIFEST)
    manifest["boot_menu"] = {
        "menu_id": "urn:srcos:boot-menu:m2-demo",
        "default_entry_id": "sourceos-recovery-current",
        "entries": [
            {
                "entry_id": "sourceos-recovery-current",
                "label": "SourceOS Recovery — current",
                "boot_release_set_id": "urn:srcos:boot-release-set:m2-demo-recovery-2026-04-26",
                "release_set_ref": "urn:srcos:release-set:m2-demo-2026-04-26",
                "boot_mode": "recovery",
                "role": "recovery",
                "default": True,
                "rollback_eligible": False,
            },
            {
                "entry_id": "sourceos-recovery-previous",
                "label": "SourceOS Recovery — previous known good",
                "boot_release_set_id": "urn:srcos:boot-release-set:m2-demo-recovery-2026-04-25",
                "release_set_ref": "urn:srcos:release-set:m2-demo-2026-04-25",
                "boot_mode": "recovery",
                "role": "rollback",
                "default": False,
                "rollback_eligible": True,
            },
        ],
    }
    return manifest


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


def test_builds_safe_recovery_plan_with_boot_menu():
    manifest = SignedBootManifest.from_dict(manifest_with_boot_menu())
    token = EnrollmentToken.from_dict(TOKEN)
    plan = build_boot_plan(manifest, token, now=datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc))
    plan_doc = plan.to_dict()
    assert plan.execute is False
    assert plan.selected_entry_id == "sourceos-recovery-current"
    assert plan_doc["boot_menu"]["default_entry_id"] == "sourceos-recovery-current"
    assert "boot-menu-bound-when-present" in plan_doc["required_proofs"]


def test_boot_menu_default_must_match_manifest():
    bad = manifest_with_boot_menu()
    bad_menu = bad["boot_menu"]
    assert isinstance(bad_menu, dict)
    bad_entries = bad_menu["entries"]
    assert isinstance(bad_entries, list)
    bad_entries[0]["boot_release_set_id"] = "urn:srcos:boot-release-set:other"
    with pytest.raises(NlbootError, match="default entry"):
        SignedBootManifest.from_dict(bad)


def test_boot_menu_rejects_duplicate_entry_ids():
    bad = manifest_with_boot_menu()
    bad_menu = bad["boot_menu"]
    assert isinstance(bad_menu, dict)
    bad_entries = bad_menu["entries"]
    assert isinstance(bad_entries, list)
    bad_entries[1]["entry_id"] = bad_entries[0]["entry_id"]
    with pytest.raises(NlbootError, match="duplicate"):
        SignedBootManifest.from_dict(bad)


def test_rollback_entry_must_be_rollback_eligible():
    bad = manifest_with_boot_menu()
    bad_menu = bad["boot_menu"]
    assert isinstance(bad_menu, dict)
    bad_entries = bad_menu["entries"]
    assert isinstance(bad_entries, list)
    bad_entries[1]["rollback_eligible"] = False
    with pytest.raises(NlbootError, match="rollback_eligible"):
        SignedBootManifest.from_dict(bad)


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
