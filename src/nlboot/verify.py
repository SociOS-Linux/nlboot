from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

FIPS_READY_ALGORITHM = "rsa-pss-sha256"
FIPS_READY_PROFILE = "fips-140-3-compatible"
ACTIVE_KEY_STATUS = "active"


class VerificationError(ValueError):
    """Raised when a signature or trusted-key check fails."""


def _parse_time(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise VerificationError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise VerificationError(f"{field} must include timezone information")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TrustedKey:
    key_ref: str
    algorithm: str
    public_key_pem: str
    status: str
    not_before: datetime | None
    not_after: datetime | None
    revoked_at: datetime | None
    revocation_reason: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrustedKey":
        key_ref = data.get("key_ref")
        algorithm = data.get("algorithm")
        public_key_pem = data.get("public_key_pem")
        status = data.get("status", ACTIVE_KEY_STATUS)
        if not isinstance(key_ref, str) or not key_ref:
            raise VerificationError("trusted key requires key_ref")
        if algorithm != FIPS_READY_ALGORITHM:
            raise VerificationError("trusted key must use rsa-pss-sha256")
        if not isinstance(public_key_pem, str) or "BEGIN PUBLIC KEY" not in public_key_pem:
            raise VerificationError("trusted key requires PEM public key")
        if status not in {"active", "retired", "revoked"}:
            raise VerificationError("trusted key status must be active, retired, or revoked")
        not_before_raw = data.get("not_before")
        not_after_raw = data.get("not_after")
        revoked_at_raw = data.get("revoked_at")
        revocation_reason = data.get("revocation_reason")
        if revocation_reason is not None and not isinstance(revocation_reason, str):
            raise VerificationError("revocation_reason must be string when present")
        return cls(
            key_ref=key_ref,
            algorithm=algorithm,
            public_key_pem=public_key_pem,
            status=status,
            not_before=_parse_time(not_before_raw, field="not_before") if isinstance(not_before_raw, str) else None,
            not_after=_parse_time(not_after_raw, field="not_after") if isinstance(not_after_raw, str) else None,
            revoked_at=_parse_time(revoked_at_raw, field="revoked_at") if isinstance(revoked_at_raw, str) else None,
            revocation_reason=revocation_reason,
        )

    def validate_lifecycle(self, *, now: datetime | None = None) -> None:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if self.status == "revoked" or self.revoked_at is not None:
            raise VerificationError(f"trusted key {self.key_ref!r} is revoked")
        if self.status != ACTIVE_KEY_STATUS:
            raise VerificationError(f"trusted key {self.key_ref!r} is not active")
        if self.not_before and current < self.not_before:
            raise VerificationError(f"trusted key {self.key_ref!r} is not active yet")
        if self.not_after and current >= self.not_after:
            raise VerificationError(f"trusted key {self.key_ref!r} is expired")


def canonical_payload(data: dict[str, Any]) -> bytes:
    unsigned = {k: v for k, v in data.items() if k != "signature_hex"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_trust_bundle_payload(data: dict[str, Any]) -> bytes:
    unsigned = {k: v for k, v in data.items() if k not in {"signature_hex", "signatures"}}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_rsa_pss_sha256(*, payload: bytes, signature_hex: str, trusted_key: TrustedKey) -> None:
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise VerificationError("signature_hex must be hex") from exc
    public_key = serialization.load_pem_public_key(trusted_key.public_key_pem.encode("utf-8"))
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise VerificationError("trusted key must be RSA")
    if public_key.key_size < 2048:
        raise VerificationError("RSA key must be at least 2048 bits")
    try:
        public_key.verify(
            signature,
            payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
    except InvalidSignature as exc:
        raise VerificationError("signature verification failed") from exc


def load_trusted_keys(data: dict[str, Any], *, now: datetime | None = None) -> dict[str, TrustedKey]:
    keys = data.get("keys")
    if not isinstance(keys, list):
        raise VerificationError("trusted key document requires keys array")
    loaded: dict[str, TrustedKey] = {}
    for item in keys:
        if not isinstance(item, dict):
            raise VerificationError("trusted key entries must be objects")
        key = TrustedKey.from_dict(item)
        key.validate_lifecycle(now=now)
        loaded[key.key_ref] = key
    return loaded


def load_verified_trust_bundle(
    data: dict[str, Any], *, root_keys: dict[str, TrustedKey], now: datetime | None = None
) -> dict[str, TrustedKey]:
    bundle_id = data.get("bundle_id")
    signer_ref = data.get("signer_ref")
    signature_hex = data.get("signature_hex")
    algorithm = data.get("signature_algorithm")
    crypto_profile = data.get("crypto_profile")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise VerificationError("trust bundle requires bundle_id")
    if not isinstance(signer_ref, str) or not signer_ref:
        raise VerificationError("trust bundle requires signer_ref")
    if not isinstance(signature_hex, str) or not signature_hex:
        raise VerificationError("trust bundle requires signature_hex")
    if algorithm != FIPS_READY_ALGORITHM:
        raise VerificationError("trust bundle signature_algorithm must be rsa-pss-sha256")
    if crypto_profile != FIPS_READY_PROFILE:
        raise VerificationError("trust bundle crypto_profile must be fips-140-3-compatible")
    signer = root_keys.get(signer_ref)
    if signer is None:
        raise VerificationError(f"no trusted root key for signer_ref={signer_ref!r}")
    signer.validate_lifecycle(now=now)
    verify_rsa_pss_sha256(
        payload=canonical_trust_bundle_payload(data),
        signature_hex=signature_hex,
        trusted_key=signer,
    )
    return load_trusted_keys(data, now=now)
