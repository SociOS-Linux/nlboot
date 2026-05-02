#!/usr/bin/env python3
"""Validate SourceOS NLBoot lifecycle contract schemas and examples.

This validator is intentionally stdlib-only. It proves that the lifecycle
schema/example files exist, parse as JSON, declare the expected kinds, and keep
critical safety invariants such as signed releases, unsigned-fallback denial,
and explicit evidence requirements.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PAIRS = [
    (
        "ReleaseSet",
        ROOT / "schemas" / "release-set.schema.v0.1.json",
        ROOT / "examples" / "release_set.m2_demo.json",
    ),
    (
        "BootReleaseSet",
        ROOT / "schemas" / "boot-release-set.schema.v0.1.json",
        ROOT / "examples" / "boot_release_set.m2_demo_recovery.json",
    ),
    (
        "LifecycleStateRecord",
        ROOT / "schemas" / "lifecycle-state-record.schema.v0.1.json",
        ROOT / "examples" / "lifecycle_state_record.m2_demo_signed.json",
    ),
]


class ValidationError(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValidationError(f"missing file: {path.relative_to(ROOT)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"expected JSON object in {path.relative_to(ROOT)}")
    return payload


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_pair(kind: str, schema_path: Path, example_path: Path) -> None:
    schema = load_json(schema_path)
    example = load_json(example_path)

    rel_schema = schema_path.relative_to(ROOT)
    rel_example = example_path.relative_to(ROOT)

    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"{rel_schema}: must use JSON Schema draft 2020-12")
    require(schema.get("type") == "object", f"{rel_schema}: must describe an object")
    require(schema.get("properties", {}).get("kind", {}).get("const") == kind, f"{rel_schema}: kind const must be {kind}")
    require(example.get("schemaVersion") == "v0.1", f"{rel_example}: schemaVersion must be v0.1")
    require(example.get("kind") == kind, f"{rel_example}: kind must be {kind}")

    if kind == "ReleaseSet":
        require(str(example.get("releaseSetId", "")).startswith("urn:srcos:release-set:"), f"{rel_example}: invalid releaseSetId")
        require(example.get("signing", {}).get("signatureRef", "").startswith("urn:srcos:signature:"), f"{rel_example}: signatureRef required")
        require(example.get("rollback", {}).get("lastKnownGoodRequired") is True, f"{rel_example}: last-known-good rollback required")
        require(example.get("evidence", {}).get("emitFingerprint") is True, f"{rel_example}: fingerprint evidence required")
    elif kind == "BootReleaseSet":
        require(str(example.get("bootReleaseSetId", "")).startswith("urn:srcos:boot-release-set:"), f"{rel_example}: invalid bootReleaseSetId")
        require(example.get("authorization", {}).get("oneTimeUseRequired") is True, f"{rel_example}: one-time enrollment required")
        require(example.get("authorization", {}).get("deviceClaimRequired") is True, f"{rel_example}: device claim required")
        require(example.get("offlineFallback", {}).get("allowUnsignedFallback") is False, f"{rel_example}: unsigned fallback must be denied")
        require(example.get("proofs", {}).get("emitAdapterRecord") is True, f"{rel_example}: adapter evidence required")
    elif kind == "LifecycleStateRecord":
        require(str(example.get("recordId", "")).startswith("urn:srcos:lifecycle-state-record:"), f"{rel_example}: invalid recordId")
        require(example.get("transition", {}).get("allowed") is True, f"{rel_example}: example transition should be allowed")
        require(example.get("policy", {}).get("approvalRequired") is True, f"{rel_example}: lifecycle approval required")
        side_effects = example.get("sideEffects", {})
        require(side_effects.get("hostMutation") is False, f"{rel_example}: signing example must not mutate host")


def main() -> int:
    try:
        for kind, schema_path, example_path in PAIRS:
            validate_pair(kind, schema_path, example_path)
            print(f"ok: {kind}")
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("OK: NLBoot lifecycle contracts validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
