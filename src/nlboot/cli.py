from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import EnrollmentToken, NlbootError, SignedBootManifest, build_boot_plan
from .verify import (
    FIPS_READY_ALGORITHM,
    FIPS_READY_PROFILE,
    VerificationError,
    canonical_payload,
    load_trusted_keys,
    verify_rsa_pss_sha256,
)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise NlbootError(f"expected JSON object in {path}")
    return data


def verify_manifest_document(manifest_doc: dict[str, Any], trusted_keys_doc: dict[str, Any], *, require_fips: bool) -> None:
    algorithm = manifest_doc.get("signature_algorithm")
    profile = manifest_doc.get("crypto_profile")
    signer_ref = manifest_doc.get("signer_ref")
    signature_hex = manifest_doc.get("signature_hex")
    if require_fips and (algorithm != FIPS_READY_ALGORITHM or profile != FIPS_READY_PROFILE):
        raise VerificationError("require-fips requires rsa-pss-sha256 and fips-140-3-compatible profile")
    if not isinstance(signer_ref, str):
        raise VerificationError("manifest signer_ref must be a string")
    if not isinstance(signature_hex, str):
        raise VerificationError("manifest signature_hex must be a string")
    trusted_keys = load_trusted_keys(trusted_keys_doc)
    trusted_key = trusted_keys.get(signer_ref)
    if trusted_key is None:
        raise VerificationError(f"no trusted key for signer_ref={signer_ref!r}")
    if trusted_key.algorithm != algorithm:
        raise VerificationError("trusted key algorithm does not match manifest")
    verify_rsa_pss_sha256(payload=canonical_payload(manifest_doc), signature_hex=signature_hex, trusted_key=trusted_key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a safe nlboot plan from a verified manifest and enrollment token")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--trusted-keys", type=Path, required=True)
    parser.add_argument("--require-fips", action="store_true")
    parser.add_argument("--now", help="Optional ISO-8601 override for tests")
    args = parser.parse_args(argv)

    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")).astimezone(timezone.utc) if args.now else None
        manifest_doc = load_json(args.manifest)
        verify_manifest_document(manifest_doc, load_json(args.trusted_keys), require_fips=args.require_fips)
        manifest = SignedBootManifest.from_dict(manifest_doc)
        token = EnrollmentToken.from_dict(load_json(args.token))
        plan = build_boot_plan(manifest, token, now=now)
    except (NlbootError, VerificationError, ValueError, json.JSONDecodeError) as exc:
        print(f"nlboot-plan: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"ok": True, "plan": plan.to_dict()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
