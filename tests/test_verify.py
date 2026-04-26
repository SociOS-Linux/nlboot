from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nlboot.verify import VerificationError, load_trusted_keys

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
