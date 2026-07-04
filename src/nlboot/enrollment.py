from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any

from .device import DeviceClaim, DeviceError
from .protocol import TokenPurpose

DEFAULT_TTL_SECONDS = 900
SESSION_TTL_SECONDS = 300
CODE_BYTES = 16


class EnrollmentError(ValueError):
    """Raised when single-use enrollment issuance or redemption fails closed."""


def _hash_code(code: str) -> str:
    """Return a SHA-256 hash of the one-time code so the binding never stores the raw secret."""

    return hashlib.sha256(code.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EnrollmentCodeBinding:
    """A single-use enrollment code bound to one device claim, release-set refs, and a TTL.

    The raw code is never stored; only ``code_hash`` is retained. ``remaining_uses`` starts at one
    and is decremented on a successful redemption, so the binding is fail-closed against replay.
    """

    code_hash: str
    purpose: TokenPurpose
    device_id: str
    nonce: str
    release_set_ref: str
    boot_release_set_ref: str
    artifact_refs: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime
    remaining_uses: int

    def is_spent(self) -> bool:
        return self.remaining_uses <= 0


@dataclass(frozen=True)
class SessionCredential:
    """A short-lived credential returned on successful redemption, plus authorized artifact refs.

    The credential is bound to the redeeming ``device_id`` and to the release set the code
    authorized; it carries no standing authority beyond ``expires_at``.
    """

    session_id: str
    device_id: str
    purpose: TokenPurpose
    release_set_ref: str
    boot_release_set_ref: str
    artifact_refs: tuple[str, ...]
    issued_at: datetime
    expires_at: datetime


@dataclass
class EnrollmentRegistry:
    """A local-first, in-memory registry of single-use enrollment-code bindings.

    There are no network calls: this is the protocol and crypto, not a web service. A control plane
    would persist these bindings, but the one-time-use, expiry, and claim-match rules live here.
    """

    _bindings: dict[str, EnrollmentCodeBinding] = field(default_factory=dict)

    def issue(
        self,
        *,
        device_claim: DeviceClaim,
        purpose: TokenPurpose,
        release_set_ref: str,
        boot_release_set_ref: str,
        artifact_refs: list[str] | tuple[str, ...],
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        now: datetime | None = None,
    ) -> tuple[str, EnrollmentCodeBinding]:
        """Issue a one-time code bound to a verified device claim and the authorized release set.

        Returns ``(raw_code, binding)``. The raw code is shown to the operator once; only its hash
        is retained. The device claim is verified (key possession + fingerprint) before issuance.
        """

        if purpose not in {"enroll", "boot", "repair", "recovery"}:
            raise EnrollmentError(f"unsupported purpose={purpose!r}")
        if ttl_seconds <= 0:
            raise EnrollmentError("ttl_seconds must be positive")
        if not release_set_ref or not isinstance(release_set_ref, str):
            raise EnrollmentError("release_set_ref must be a non-empty string")
        if not boot_release_set_ref or not isinstance(boot_release_set_ref, str):
            raise EnrollmentError("boot_release_set_ref must be a non-empty string")
        refs = tuple(artifact_refs)
        if not refs or not all(isinstance(r, str) and r for r in refs):
            raise EnrollmentError("artifact_refs must be a non-empty list of strings")
        try:
            device_claim.verify(expected_nonce=device_claim.nonce)
        except DeviceError as exc:
            raise EnrollmentError(f"device claim is invalid: {exc}") from exc

        issued_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        code = secrets.token_urlsafe(CODE_BYTES)
        binding = EnrollmentCodeBinding(
            code_hash=_hash_code(code),
            purpose=purpose,
            device_id=device_claim.device_id,
            nonce=device_claim.nonce,
            release_set_ref=release_set_ref,
            boot_release_set_ref=boot_release_set_ref,
            artifact_refs=refs,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
            remaining_uses=1,
        )
        self._bindings[binding.code_hash] = binding
        return code, binding

    def redeem(
        self,
        *,
        code: str,
        device_claim: DeviceClaim,
        release_set_ref: str,
        session_ttl_seconds: int = SESSION_TTL_SECONDS,
        now: datetime | None = None,
    ) -> SessionCredential:
        """Exchange ``code`` + a fresh device claim for a short-lived session credential.

        Fails closed on: unknown/spent code, expiry, device-claim mismatch (wrong device, bad
        signature, or wrong nonce), and release-set-ref mismatch. On success the binding's
        remaining-use counter is decremented so the code can never be redeemed twice.
        """

        if not code or not isinstance(code, str):
            raise EnrollmentError("code must be a non-empty string")
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        binding = self._bindings.get(_hash_code(code))
        if binding is None:
            raise EnrollmentError("enrollment code is unknown")
        if binding.is_spent():
            raise EnrollmentError("enrollment code has already been redeemed")
        if current >= binding.expires_at:
            raise EnrollmentError("enrollment code is expired")
        if release_set_ref != binding.release_set_ref:
            raise EnrollmentError("release_set_ref does not match the issued enrollment code")

        # The redeeming claim must prove the SAME device the code was bound to, against the bound
        # nonce. verify() enforces fingerprint match + key possession; we then bind device + nonce.
        try:
            device_claim.verify(expected_nonce=binding.nonce)
        except DeviceError as exc:
            raise EnrollmentError(f"device claim is invalid: {exc}") from exc
        if device_claim.device_id != binding.device_id:
            raise EnrollmentError("device claim does not match the device the code was issued to")

        # Spend the single use atomically before returning the credential (fail-closed on replay).
        self._bindings[binding.code_hash] = replace(binding, remaining_uses=binding.remaining_uses - 1)

        return SessionCredential(
            session_id=f"urn:srcos:enrollment-session:{secrets.token_hex(CODE_BYTES)}",
            device_id=binding.device_id,
            purpose=binding.purpose,
            release_set_ref=binding.release_set_ref,
            boot_release_set_ref=binding.boot_release_set_ref,
            artifact_refs=binding.artifact_refs,
            issued_at=current,
            expires_at=current + timedelta(seconds=session_ttl_seconds),
        )

    def binding_for(self, code: str) -> EnrollmentCodeBinding | None:
        return self._bindings.get(_hash_code(code))


def issue_enrollment_token_payload(
    binding: EnrollmentCodeBinding, *, token_id: str, subject_kind: str = "device"
) -> dict[str, Any]:
    """Render an issued :class:`~nlboot.protocol.EnrollmentToken` payload from a code binding.

    This is the bridge to the existing token-validation path: the dict it returns parses with
    ``EnrollmentToken.from_dict`` and validates with ``validate_for_manifest`` (no duplication of
    those checks here).
    """

    return {
        "token_id": token_id,
        "purpose": binding.purpose,
        "audience": {"subject_kind": subject_kind, "subject_id": binding.device_id},
        "release_set_ref": binding.release_set_ref,
        "boot_release_set_ref": binding.boot_release_set_ref,
        "one_time_use": True,
        "issued_at": binding.issued_at.isoformat().replace("+00:00", "Z"),
        "expires_at": binding.expires_at.isoformat().replace("+00:00", "Z"),
        "status": "issued",
    }
