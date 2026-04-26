from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

BootMode = Literal["installer", "recovery", "ephemeral", "bootstrap"]
TokenPurpose = Literal["enroll", "boot", "repair", "recovery"]
PlanAction = Literal["present-menu", "boot-recovery", "boot-installer", "boot-ephemeral", "bootstrap-only"]
SignatureAlgorithm = Literal["rsa-pss-sha256"]
CryptoProfile = Literal["fips-140-3-compatible"]
FIPS_READY_ALGORITHM = "rsa-pss-sha256"
FIPS_READY_PROFILE = "fips-140-3-compatible"


class NlbootError(ValueError):
    """Raised when an nlboot protocol object is invalid or unsafe."""


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise NlbootError(f"{key} must be a non-empty string")
    return value


def _parse_time(value: str, *, key: str) -> datetime:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise NlbootError(f"{key} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise NlbootError(f"{key} must include timezone information")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class SignedBootManifest:
    """FIPS-ready signed boot manifest contract used by the safe planner.

    The protocol requires RSA-PSS/SHA-256 metadata and an explicit FIPS-ready profile. Full FIPS
    compliance still depends on executing cryptography in a validated runtime module.
    """

    manifest_id: str
    boot_release_set_id: str
    base_release_set_ref: str
    boot_mode: BootMode
    artifacts: dict[str, str]
    signature_ref: str
    signer_ref: str
    signature_algorithm: SignatureAlgorithm
    crypto_profile: CryptoProfile
    signature_hex: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SignedBootManifest":
        manifest_id = _require_string(data, "manifest_id")
        boot_release_set_id = _require_string(data, "boot_release_set_id")
        base_release_set_ref = _require_string(data, "base_release_set_ref")
        signature_ref = _require_string(data, "signature_ref")
        signer_ref = _require_string(data, "signer_ref")
        signature_algorithm = _require_string(data, "signature_algorithm")
        crypto_profile = _require_string(data, "crypto_profile")
        signature_hex = _require_string(data, "signature_hex")
        if signature_algorithm != FIPS_READY_ALGORITHM:
            raise NlbootError("signature_algorithm must be rsa-pss-sha256")
        if crypto_profile != FIPS_READY_PROFILE:
            raise NlbootError("crypto_profile must be fips-140-3-compatible")
        boot_mode = _require_string(data, "boot_mode")
        if boot_mode not in {"installer", "recovery", "ephemeral", "bootstrap"}:
            raise NlbootError(f"unsupported boot_mode={boot_mode!r}")
        artifacts = data.get("artifacts")
        if not isinstance(artifacts, dict):
            raise NlbootError("artifacts must be an object")
        required_artifacts = {"kernel_ref", "initrd_ref", "rootfs_ref"}
        missing = sorted(k for k in required_artifacts if not isinstance(artifacts.get(k), str) or not artifacts.get(k))
        if missing:
            raise NlbootError("artifacts missing required refs: " + ", ".join(missing))
        if not signature_ref.startswith("urn:srcos:signature:"):
            raise NlbootError("signature_ref must be a SourceOS signature URN")
        return cls(
            manifest_id=manifest_id,
            boot_release_set_id=boot_release_set_id,
            base_release_set_ref=base_release_set_ref,
            boot_mode=boot_mode,  # type: ignore[arg-type]
            artifacts={k: str(v) for k, v in artifacts.items()},
            signature_ref=signature_ref,
            signer_ref=signer_ref,
            signature_algorithm=signature_algorithm,  # type: ignore[arg-type]
            crypto_profile=crypto_profile,  # type: ignore[arg-type]
            signature_hex=signature_hex,
        )


@dataclass(frozen=True)
class EnrollmentToken:
    token_id: str
    purpose: TokenPurpose
    subject_kind: str
    subject_id: str | None
    release_set_ref: str | None
    boot_release_set_ref: str | None
    one_time_use: bool
    issued_at: datetime
    expires_at: datetime
    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnrollmentToken":
        token_id = _require_string(data, "token_id")
        purpose = _require_string(data, "purpose")
        if purpose not in {"enroll", "boot", "repair", "recovery"}:
            raise NlbootError(f"unsupported purpose={purpose!r}")
        audience = data.get("audience")
        if not isinstance(audience, dict):
            raise NlbootError("audience must be an object")
        subject_kind = _require_string(audience, "subject_kind")
        subject_id = audience.get("subject_id")
        if subject_id is not None and not isinstance(subject_id, str):
            raise NlbootError("audience.subject_id must be null or string")
        issued_at = _parse_time(_require_string(data, "issued_at"), key="issued_at")
        expires_at = _parse_time(_require_string(data, "expires_at"), key="expires_at")
        one_time_use = data.get("one_time_use")
        if not isinstance(one_time_use, bool):
            raise NlbootError("one_time_use must be boolean")
        status = _require_string(data, "status")
        if status not in {"issued", "redeemed", "expired", "revoked"}:
            raise NlbootError(f"unsupported status={status!r}")
        return cls(
            token_id=token_id,
            purpose=purpose,  # type: ignore[arg-type]
            subject_kind=subject_kind,
            subject_id=subject_id,
            release_set_ref=data.get("release_set_ref"),
            boot_release_set_ref=data.get("boot_release_set_ref"),
            one_time_use=one_time_use,
            issued_at=issued_at,
            expires_at=expires_at,
            status=status,
        )

    def validate_for_manifest(self, manifest: SignedBootManifest, *, now: datetime | None = None) -> None:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if self.status != "issued":
            raise NlbootError(f"token status must be issued, got {self.status!r}")
        if current >= self.expires_at:
            raise NlbootError("token is expired")
        if self.one_time_use is not True:
            raise NlbootError("token must be one-time use")
        if self.boot_release_set_ref != manifest.boot_release_set_id:
            raise NlbootError("token boot_release_set_ref does not match manifest")
        if self.release_set_ref != manifest.base_release_set_ref:
            raise NlbootError("token release_set_ref does not match manifest base release")
        purpose_by_mode = {
            "recovery": {"recovery", "repair"},
            "installer": {"enroll", "boot"},
            "ephemeral": {"boot"},
            "bootstrap": {"enroll", "boot"},
        }
        if self.purpose not in purpose_by_mode[manifest.boot_mode]:
            raise NlbootError(f"token purpose {self.purpose!r} is not valid for boot_mode {manifest.boot_mode!r}")


@dataclass(frozen=True)
class BootPlan:
    action: PlanAction
    manifest_id: str
    boot_release_set_id: str
    release_set_ref: str
    artifacts: dict[str, str]
    authorized_by: str
    signature_algorithm: str
    crypto_profile: str
    execute: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "manifest_id": self.manifest_id,
            "boot_release_set_id": self.boot_release_set_id,
            "release_set_ref": self.release_set_ref,
            "artifacts": self.artifacts,
            "authorized_by": self.authorized_by,
            "signature_algorithm": self.signature_algorithm,
            "crypto_profile": self.crypto_profile,
            "execute": self.execute,
        }


def build_boot_plan(manifest: SignedBootManifest, token: EnrollmentToken, *, now: datetime | None = None) -> BootPlan:
    token.validate_for_manifest(manifest, now=now)
    action_by_mode: dict[BootMode, PlanAction] = {
        "recovery": "boot-recovery",
        "installer": "boot-installer",
        "ephemeral": "boot-ephemeral",
        "bootstrap": "bootstrap-only",
    }
    return BootPlan(
        action=action_by_mode[manifest.boot_mode],
        manifest_id=manifest.manifest_id,
        boot_release_set_id=manifest.boot_release_set_id,
        release_set_ref=manifest.base_release_set_ref,
        artifacts=manifest.artifacts,
        authorized_by=token.token_id,
        signature_algorithm=manifest.signature_algorithm,
        crypto_profile=manifest.crypto_profile,
        execute=False,
    )
