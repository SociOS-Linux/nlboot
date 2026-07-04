from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

FIPS_READY_ALGORITHM = "rsa-pss-sha256"
FIPS_READY_PROFILE = "fips-140-3-compatible"
DEVICE_ID_PREFIX = "urn:srcos:device:"
RSA_PUBLIC_EXPONENT = 65537
RSA_KEY_SIZE = 2048
PSS_SALT_LENGTH = 32


class DeviceError(ValueError):
    """Raised when a device identity or device claim is invalid or unsafe."""


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DeviceError(f"{key} must be a non-empty string")
    return value


def _parse_time(value: str, *, key: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DeviceError(f"{key} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise DeviceError(f"{key} must include timezone information")
    return parsed.astimezone(timezone.utc)


def _public_key_pem(public_key: rsa.RSAPublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")


def _load_public_key(public_key_pem: str) -> rsa.RSAPublicKey:
    if "BEGIN PUBLIC KEY" not in public_key_pem:
        raise DeviceError("device public key must be a PEM SubjectPublicKeyInfo block")
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    except ValueError as exc:
        raise DeviceError("device public key is not valid PEM") from exc
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise DeviceError("device key must be RSA")
    if public_key.key_size < RSA_KEY_SIZE:
        raise DeviceError(f"device RSA key must be at least {RSA_KEY_SIZE} bits")
    return public_key


def device_fingerprint(public_key_pem: str) -> str:
    """Return the stable device id derived from the SubjectPublicKeyInfo DER bytes.

    The fingerprint is SHA-256 over the canonical DER public-key encoding, so the same key
    always yields the same device id regardless of PEM whitespace.
    """

    public_key = _load_public_key(public_key_pem)
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    digest = hashlib.sha256(der).hexdigest()
    return f"{DEVICE_ID_PREFIX}sha256:{digest}"


@dataclass(frozen=True)
class DeviceIdentity:
    """A locally generated device keypair whose public-key fingerprint is the stable device id.

    The private key never leaves the device; only the public key (or its fingerprint) is presented
    at enrollment. Signing uses RSA-PSS/SHA-256 to match the rest of the nlboot protocol.
    """

    device_id: str
    public_key_pem: str
    _private_key: rsa.RSAPrivateKey

    @classmethod
    def generate(cls) -> "DeviceIdentity":
        private_key = rsa.generate_private_key(
            public_exponent=RSA_PUBLIC_EXPONENT,
            key_size=RSA_KEY_SIZE,
        )
        public_key_pem = _public_key_pem(private_key.public_key())
        return cls(
            device_id=device_fingerprint(public_key_pem),
            public_key_pem=public_key_pem,
            _private_key=private_key,
        )

    @classmethod
    def from_private_key_pem(cls, private_key_pem: str, *, password: bytes | None = None) -> "DeviceIdentity":
        try:
            private_key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=password)
        except (ValueError, TypeError) as exc:
            raise DeviceError("device private key is not valid PEM") from exc
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise DeviceError("device private key must be RSA")
        public_key_pem = _public_key_pem(private_key.public_key())
        return cls(
            device_id=device_fingerprint(public_key_pem),
            public_key_pem=public_key_pem,
            _private_key=private_key,
        )

    def private_key_pem(self) -> str:
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

    def _sign(self, payload: bytes) -> str:
        signature = self._private_key.sign(
            payload,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=PSS_SALT_LENGTH),
            hashes.SHA256(),
        )
        return signature.hex()

    def make_claim(self, *, nonce: str, claimed_at: datetime | None = None) -> "DeviceClaim":
        """Produce a self-signed device claim presenting the public key and a fresh nonce.

        The nonce binds the claim to a single enrollment attempt; the issuer supplies it so a
        captured claim cannot be replayed against a different code.
        """

        if not isinstance(nonce, str) or not nonce.strip():
            raise DeviceError("nonce must be a non-empty string")
        when = (claimed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        payload = DeviceClaim._signing_payload(
            device_id=self.device_id,
            public_key_pem=self.public_key_pem,
            nonce=nonce,
            claimed_at=when,
        )
        return DeviceClaim(
            device_id=self.device_id,
            public_key_pem=self.public_key_pem,
            nonce=nonce,
            claimed_at=when,
            signature_algorithm=FIPS_READY_ALGORITHM,
            crypto_profile=FIPS_READY_PROFILE,
            signature_hex=self._sign(payload),
        )


@dataclass(frozen=True)
class DeviceClaim:
    """An ephemeral, self-signed assertion of device identity presented at enrollment.

    The claim proves possession of the private key matching ``public_key_pem`` over a one-time
    ``nonce``. ``device_id`` MUST equal the fingerprint of ``public_key_pem`` or the claim is
    rejected, so a device cannot assert an id it does not hold the key for.
    """

    device_id: str
    public_key_pem: str
    nonce: str
    claimed_at: datetime
    signature_algorithm: str
    crypto_profile: str
    signature_hex: str

    @staticmethod
    def _signing_payload(*, device_id: str, public_key_pem: str, nonce: str, claimed_at: datetime) -> bytes:
        import json

        unsigned = {
            "device_id": device_id,
            "public_key_pem": public_key_pem,
            "nonce": nonce,
            "claimed_at": claimed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceClaim":
        device_id = _require_string(data, "device_id")
        public_key_pem = _require_string(data, "public_key_pem")
        nonce = _require_string(data, "nonce")
        claimed_at = _parse_time(_require_string(data, "claimed_at"), key="claimed_at")
        signature_algorithm = _require_string(data, "signature_algorithm")
        crypto_profile = _require_string(data, "crypto_profile")
        signature_hex = _require_string(data, "signature_hex")
        if signature_algorithm != FIPS_READY_ALGORITHM:
            raise DeviceError("signature_algorithm must be rsa-pss-sha256")
        if crypto_profile != FIPS_READY_PROFILE:
            raise DeviceError("crypto_profile must be fips-140-3-compatible")
        if not device_id.startswith(DEVICE_ID_PREFIX):
            raise DeviceError("device_id must be a SourceOS device URN")
        return cls(
            device_id=device_id,
            public_key_pem=public_key_pem,
            nonce=nonce,
            claimed_at=claimed_at,
            signature_algorithm=signature_algorithm,
            crypto_profile=crypto_profile,
            signature_hex=signature_hex,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "public_key_pem": self.public_key_pem,
            "nonce": self.nonce,
            "claimed_at": self.claimed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "signature_algorithm": self.signature_algorithm,
            "crypto_profile": self.crypto_profile,
            "signature_hex": self.signature_hex,
        }

    def verify(self, *, expected_nonce: str | None = None) -> None:
        """Fail closed unless the claim is internally consistent and proves key possession.

        Checks: (1) ``device_id`` equals the fingerprint of the presented public key, (2) the
        self-signature verifies under that public key, and (3) the nonce matches ``expected_nonce``
        when the issuer supplies one.
        """

        if device_fingerprint(self.public_key_pem) != self.device_id:
            raise DeviceError("device_id does not match presented public key fingerprint")
        if expected_nonce is not None and self.nonce != expected_nonce:
            raise DeviceError("device claim nonce does not match expected nonce")
        public_key = _load_public_key(self.public_key_pem)
        try:
            signature = bytes.fromhex(self.signature_hex)
        except ValueError as exc:
            raise DeviceError("signature_hex must be hex") from exc
        payload = self._signing_payload(
            device_id=self.device_id,
            public_key_pem=self.public_key_pem,
            nonce=self.nonce,
            claimed_at=self.claimed_at,
        )
        try:
            public_key.verify(
                signature,
                payload,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=PSS_SALT_LENGTH),
                hashes.SHA256(),
            )
        except InvalidSignature as exc:
            raise DeviceError("device claim signature verification failed") from exc
