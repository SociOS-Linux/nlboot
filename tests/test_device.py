from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nlboot.device import DeviceClaim, DeviceError, DeviceIdentity, device_fingerprint


def now() -> datetime:
    return datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc)


def test_generate_yields_stable_fingerprint_device_id():
    identity = DeviceIdentity.generate()
    assert identity.device_id.startswith("urn:srcos:device:sha256:")
    # The device id is the fingerprint of the public key, independent of PEM round-trips.
    assert identity.device_id == device_fingerprint(identity.public_key_pem)


def test_round_trip_private_key_pem_preserves_device_id():
    identity = DeviceIdentity.generate()
    reloaded = DeviceIdentity.from_private_key_pem(identity.private_key_pem())
    assert reloaded.device_id == identity.device_id
    assert reloaded.public_key_pem == identity.public_key_pem


def test_distinct_keys_yield_distinct_device_ids():
    assert DeviceIdentity.generate().device_id != DeviceIdentity.generate().device_id


def test_claim_creation_and_verification_succeeds():
    identity = DeviceIdentity.generate()
    claim = identity.make_claim(nonce="nonce-abc", claimed_at=now())
    assert claim.device_id == identity.device_id
    assert claim.signature_algorithm == "rsa-pss-sha256"
    assert claim.crypto_profile == "fips-140-3-compatible"
    # Verifies under the presented public key, with and without an expected nonce.
    claim.verify()
    claim.verify(expected_nonce="nonce-abc")


def test_claim_serializes_and_parses_round_trip():
    identity = DeviceIdentity.generate()
    claim = identity.make_claim(nonce="nonce-rt", claimed_at=now())
    parsed = DeviceClaim.from_dict(claim.to_dict())
    parsed.verify(expected_nonce="nonce-rt")
    assert parsed == claim


def test_claim_rejects_wrong_expected_nonce():
    claim = DeviceIdentity.generate().make_claim(nonce="nonce-real", claimed_at=now())
    with pytest.raises(DeviceError, match="nonce"):
        claim.verify(expected_nonce="nonce-other")


def test_claim_rejects_spoofed_device_id():
    identity = DeviceIdentity.generate()
    claim = identity.make_claim(nonce="nonce-x", claimed_at=now())
    spoofed = DeviceClaim(
        device_id="urn:srcos:device:sha256:" + "0" * 64,
        public_key_pem=claim.public_key_pem,
        nonce=claim.nonce,
        claimed_at=claim.claimed_at,
        signature_algorithm=claim.signature_algorithm,
        crypto_profile=claim.crypto_profile,
        signature_hex=claim.signature_hex,
    )
    with pytest.raises(DeviceError, match="fingerprint"):
        spoofed.verify()


def test_claim_rejects_substituted_public_key():
    # A claim that presents a different key than the one that produced the signature must fail.
    victim = DeviceIdentity.generate().make_claim(nonce="nonce-y", claimed_at=now())
    attacker = DeviceIdentity.generate()
    forged = DeviceClaim(
        device_id=device_fingerprint(attacker.public_key_pem),
        public_key_pem=attacker.public_key_pem,
        nonce=victim.nonce,
        claimed_at=victim.claimed_at,
        signature_algorithm=victim.signature_algorithm,
        crypto_profile=victim.crypto_profile,
        signature_hex=victim.signature_hex,
    )
    with pytest.raises(DeviceError, match="signature verification failed"):
        forged.verify()


def test_claim_rejects_non_fips_algorithm():
    claim = DeviceIdentity.generate().make_claim(nonce="nonce-z", claimed_at=now())
    data = claim.to_dict()
    data["signature_algorithm"] = "ed25519"
    with pytest.raises(DeviceError, match="rsa-pss-sha256"):
        DeviceClaim.from_dict(data)
