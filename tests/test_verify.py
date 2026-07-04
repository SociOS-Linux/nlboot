from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nlboot import verify
from nlboot.verify import VerificationError, load_trusted_keys, load_verified_trust_bundle

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArBfEOS4UzauNLkcJB/JY
UQy0qkPOyyj1Zm2dLd00KXxeoj6JnfUtqIsYz7lmiWOKQf4bJlpbl3acKkSSdIDv
o3h32zqNDBO8vlnX26ym7qBRhWd9BR6CZ5/+Qu/AYcMbbtQf5OYK65BBWEZQGDE1
56ihXzaWoxZDAHt0FZpD8PgtCaCcXT5qmLYhk207cVdVpxJ9+knWisu2F6KPcgOh
WwBevbIFfv/QYac0LupV/bXpGFiNMVbfWgHIT1s4plFXRBtdJG4maoIc8B6ln2pT
+nDHozjCWDloI322WGabunZyZRrNzdg1eWM0Xk5XH1zeo+7hcxvjvUJeOVQtDs5v
twIDAQAB
-----END PUBLIC KEY-----
"""


def key_doc(**overrides: object) -> dict[str, object]:
    key = {
        "key_ref": "urn:srcos:key:sourceos-release-root",
        "algorithm": "rsa-pss-sha256",
        "public_key_pem": PUBLIC_KEY,
        "status": "active",
        "not_before": "2026-04-01T00:00:00Z",
        "not_after": "2026-05-01T00:00:00Z",
    }
    key.update(overrides)
    return {"keys": [key]}


def trust_bundle(**overrides: object) -> dict[str, object]:
    bundle = key_doc()
    bundle.update(
        {
            "bundle_id": "urn:srcos:trust-bundle:m2-demo-2026-04-26",
            "signer_ref": "urn:srcos:key:sourceos-release-root",
            "signature_algorithm": "rsa-pss-sha256",
            "crypto_profile": "fips-140-3-compatible",
            "signature_hex": "00",
        }
    )
    bundle.update(overrides)
    return bundle


def now() -> datetime:
    return datetime(2026, 4, 26, 14, 35, tzinfo=timezone.utc)


def test_active_key_loads_inside_validity_window():
    keys = load_trusted_keys(key_doc(), now=now())
    assert "urn:srcos:key:sourceos-release-root" in keys


def test_future_key_rejected():
    with pytest.raises(VerificationError, match="not active yet"):
        load_trusted_keys(key_doc(not_before="2026-04-27T00:00:00Z"), now=now())


def test_expired_key_rejected():
    with pytest.raises(VerificationError, match="expired"):
        load_trusted_keys(key_doc(not_after="2026-04-26T14:00:00Z"), now=now())


def test_retired_key_rejected():
    with pytest.raises(VerificationError, match="not active"):
        load_trusted_keys(key_doc(status="retired"), now=now())


def test_revoked_key_rejected():
    with pytest.raises(VerificationError, match="revoked"):
        load_trusted_keys(
            key_doc(
                status="revoked",
                revoked_at="2026-04-20T00:00:00Z",
                revocation_reason="compromised",
            ),
            now=now(),
        )


def test_signed_trust_bundle_loads_after_root_verification(monkeypatch: pytest.MonkeyPatch):
    calls: list[bytes] = []

    def fake_verify(*, payload: bytes, signature_hex: str, trusted_key: object) -> None:
        calls.append(payload)
        assert signature_hex == "00"

    root_keys = load_trusted_keys(key_doc(), now=now())
    monkeypatch.setattr(verify, "verify_rsa_pss_sha256", fake_verify)
    keys = load_verified_trust_bundle(trust_bundle(), root_keys=root_keys, now=now())
    assert "urn:srcos:key:sourceos-release-root" in keys
    assert calls == [verify.canonical_trust_bundle_payload(trust_bundle())]


def test_signed_trust_bundle_requires_root_signer():
    with pytest.raises(VerificationError, match="no trusted root key"):
        load_verified_trust_bundle(trust_bundle(signer_ref="urn:srcos:key:missing"), root_keys={}, now=now())


def test_signed_trust_bundle_rejects_non_fips_algorithm():
    root_keys = load_trusted_keys(key_doc(), now=now())
    with pytest.raises(VerificationError, match="signature_algorithm"):
        load_verified_trust_bundle(trust_bundle(signature_algorithm="ed25519"), root_keys=root_keys, now=now())


def test_signed_trust_bundle_rejects_revoked_root(monkeypatch: pytest.MonkeyPatch):
    def fake_verify(*, payload: bytes, signature_hex: str, trusted_key: object) -> None:
        assert payload == verify.canonical_trust_bundle_payload(bundle)
        assert signature_hex == "00"

    root_keys = load_trusted_keys(key_doc(), now=now())
    revoked_root = key_doc(status="revoked", revoked_at="2026-04-20T00:00:00Z")
    bundle = trust_bundle(keys=revoked_root["keys"])
    monkeypatch.setattr(verify, "verify_rsa_pss_sha256", fake_verify)
    with pytest.raises(VerificationError, match="revoked"):
        load_verified_trust_bundle(bundle, root_keys=root_keys, now=now())
