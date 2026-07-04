from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from nlboot.device import DeviceIdentity
from nlboot.enrollment import (
    EnrollmentError,
    EnrollmentRegistry,
    issue_enrollment_token_payload,
)
from nlboot.protocol import EnrollmentToken, SignedBootManifest, build_boot_plan

RELEASE_SET_REF = "urn:srcos:release-set:m2-demo-2026-04-26"
BOOT_RELEASE_SET_REF = "urn:srcos:boot-release-set:m2-demo-recovery-2026-04-26"
ARTIFACTS = [
    "urn:srcos:artifact:m2-demo-kernel",
    "urn:srcos:artifact:m2-demo-initrd",
    "urn:srcos:artifact:m2-demo-rootfs",
]


def now() -> datetime:
    return datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc)


def _issue(registry: EnrollmentRegistry, identity: DeviceIdentity, *, nonce: str = "nonce-1", at: datetime | None = None):
    claim = identity.make_claim(nonce=nonce, claimed_at=at or now())
    return registry.issue(
        device_claim=claim,
        purpose="recovery",
        release_set_ref=RELEASE_SET_REF,
        boot_release_set_ref=BOOT_RELEASE_SET_REF,
        artifact_refs=ARTIFACTS,
        ttl_seconds=900,
        now=at or now(),
    )


def test_issue_binds_one_time_code_to_device_and_release_set():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, binding = _issue(registry, identity)
    assert code  # raw code returned exactly once
    assert binding.device_id == identity.device_id
    assert binding.release_set_ref == RELEASE_SET_REF
    assert binding.remaining_uses == 1
    # The raw code is never stored; only its hash is retained.
    assert code not in binding.code_hash
    assert registry.binding_for(code) is binding


def test_successful_redemption_returns_session_and_artifact_refs():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, _ = _issue(registry, identity)
    claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    cred = registry.redeem(code=code, device_claim=claim, release_set_ref=RELEASE_SET_REF, now=now())
    assert cred.device_id == identity.device_id
    assert cred.purpose == "recovery"
    assert cred.release_set_ref == RELEASE_SET_REF
    assert tuple(cred.artifact_refs) == tuple(ARTIFACTS)
    assert cred.expires_at > cred.issued_at
    # The single use is now spent.
    assert registry.binding_for(code).is_spent()


def test_reused_code_fails_closed():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, _ = _issue(registry, identity)
    claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    registry.redeem(code=code, device_claim=claim, release_set_ref=RELEASE_SET_REF, now=now())
    with pytest.raises(EnrollmentError, match="already been redeemed"):
        registry.redeem(code=code, device_claim=claim, release_set_ref=RELEASE_SET_REF, now=now())


def test_expired_code_fails_closed():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, binding = _issue(registry, identity)
    claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    after_expiry = binding.expires_at + timedelta(seconds=1)
    with pytest.raises(EnrollmentError, match="expired"):
        registry.redeem(code=code, device_claim=claim, release_set_ref=RELEASE_SET_REF, now=after_expiry)


def test_wrong_device_claim_fails_closed():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, _ = _issue(registry, identity)
    # A different device presents a (valid) claim for the same nonce; it must not redeem the code.
    attacker = DeviceIdentity.generate()
    attacker_claim = attacker.make_claim(nonce="nonce-1", claimed_at=now())
    with pytest.raises(EnrollmentError, match="does not match the device"):
        registry.redeem(code=code, device_claim=attacker_claim, release_set_ref=RELEASE_SET_REF, now=now())
    # And the code remains unspent and usable by the legitimate device afterwards.
    legit_claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    cred = registry.redeem(code=code, device_claim=legit_claim, release_set_ref=RELEASE_SET_REF, now=now())
    assert cred.device_id == identity.device_id


def test_wrong_release_set_ref_fails_closed():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, _ = _issue(registry, identity)
    claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    with pytest.raises(EnrollmentError, match="release_set_ref"):
        registry.redeem(code=code, device_claim=claim, release_set_ref="urn:srcos:release-set:other", now=now())


def test_unknown_code_fails_closed():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    with pytest.raises(EnrollmentError, match="unknown"):
        registry.redeem(code="never-issued", device_claim=claim, release_set_ref=RELEASE_SET_REF, now=now())


def test_issue_rejects_invalid_device_claim():
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    claim = identity.make_claim(nonce="nonce-1", claimed_at=now())
    tampered = claim.to_dict()
    tampered["signature_hex"] = "00"
    from nlboot.device import DeviceClaim

    bad = DeviceClaim.from_dict(tampered)
    with pytest.raises(EnrollmentError, match="device claim is invalid"):
        registry.issue(
            device_claim=bad,
            purpose="recovery",
            release_set_ref=RELEASE_SET_REF,
            boot_release_set_ref=BOOT_RELEASE_SET_REF,
            artifact_refs=ARTIFACTS,
            now=now(),
        )


def test_binding_bridges_to_existing_enrollment_token_validation():
    # The issued binding renders a token payload that flows through the EXISTING validation path
    # (EnrollmentToken.from_dict + build_boot_plan), proving no duplication of those checks.
    registry = EnrollmentRegistry()
    identity = DeviceIdentity.generate()
    code, binding = _issue(registry, identity)
    assert code
    payload = issue_enrollment_token_payload(binding, token_id="urn:srcos:enrollment-token:m2-demo-recovery")
    token = EnrollmentToken.from_dict(payload)
    manifest = SignedBootManifest.from_dict(
        {
            "manifest_id": "urn:srcos:boot-manifest:m2-demo-recovery",
            "boot_release_set_id": BOOT_RELEASE_SET_REF,
            "base_release_set_ref": RELEASE_SET_REF,
            "boot_mode": "recovery",
            "artifacts": {
                "kernel_ref": ARTIFACTS[0],
                "initrd_ref": ARTIFACTS[1],
                "rootfs_ref": ARTIFACTS[2],
            },
            "signature_ref": "urn:srcos:signature:m2-demo-recovery",
            "signer_ref": "urn:srcos:key:sourceos-release-root",
            "signature_algorithm": "rsa-pss-sha256",
            "crypto_profile": "fips-140-3-compatible",
            "signature_hex": "00",
        }
    )
    plan = build_boot_plan(manifest, token, now=now())
    assert plan.action == "boot-recovery"
    assert plan.execute is False
