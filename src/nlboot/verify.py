from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

FIPS_READY_ALGORITHM = "rsa-pss-sha256"
FIPS_READY_PROFILE = "fips-140-3-compatible"


class VerificationError(ValueError):
    """Raised when a signature or trusted-key check fails."""


@dataclass(frozen=True)
class TrustedKey:
    key_ref: str
    algorithm: str
    public_key_pem: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrustedKey":
        key_ref = data.get("key_ref")
        algorithm = data.get("algorithm")
        public_key_pem = data.get("public_key_pem")
        if not isinstance(key_ref, str) or not key_ref:
            raise VerificationError("trusted key requires key_ref")
        if algorithm != FIPS_READY_ALGORITHM:
            raise VerificationError("trusted key must use rsa-pss-sha256")
        if not isinstance(public_key_pem, str) or "BEGIN PUBLIC KEY" not in public_key_pem:
            raise VerificationError("trusted key requires PEM public key")
        return cls(key_ref=key_ref, algorithm=algorithm, public_key_pem=public_key_pem)


def load_trusted_keys(data: dict[str, Any]) -> dict[str, TrustedKey]:
    keys = data.get("keys")
    if not isinstance(keys, list):
        raise VerificationError("trusted key document requires keys array")
    loaded: dict[str, TrustedKey] = {}
    for item in keys:
        if not isinstance(item, dict):
            raise VerificationError("trusted key entries must be objects")
        key = TrustedKey.from_dict(item)
        loaded[key.key_ref] = key
    return loaded


def canonical_payload(data: dict[str, Any]) -> bytes:
    unsigned = {k: v for k, v in data.items() if k != "signature_hex"}
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
