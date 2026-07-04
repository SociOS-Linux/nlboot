#!/usr/bin/env python3
"""Validate repository JSON schema contract stubs and fixtures."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    (
        ROOT / "schemas" / "boot-evidence.schema.json",
        ROOT / "fixtures" / "boot-evidence.valid.json",
        "svc.managed.boot-evidence",
    )
]

REQUIRED_KEYS = {"$schema", "$id", "title", "type", "properties"}


def main() -> int:
    for schema_path, fixture_path, service_id in CHECKS:
        if not schema_path.exists():
            print(f"ERROR: missing {schema_path.relative_to(ROOT)}")
            return 1
        if not fixture_path.exists():
            print(f"ERROR: missing {fixture_path.relative_to(ROOT)}")
            return 1
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON: {exc}")
            return 1
        missing = sorted(REQUIRED_KEYS - set(schema))
        if missing:
            print(f"ERROR: {schema_path.relative_to(ROOT)} missing keys {missing}")
            return 1
        if schema.get("type") != "object":
            print(f"ERROR: {schema_path.relative_to(ROOT)} type must be object")
            return 1
        for key in schema.get("required", []):
            if key not in fixture:
                print(f"ERROR: {fixture_path.relative_to(ROOT)} missing required key {key}")
                return 1
        if fixture.get("service_id") != service_id:
            print(f"ERROR: fixture service_id {fixture.get('service_id')} != {service_id}")
            return 1
        print(f"OK: {schema_path.relative_to(ROOT)} + {fixture_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
