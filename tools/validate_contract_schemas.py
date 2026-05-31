#!/usr/bin/env python3
"""Validate repository JSON schema contract stubs."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATHS = [
    ROOT / "schemas" / "boot-evidence.schema.json",
]

REQUIRED_KEYS = {"$schema", "$id", "title", "type", "properties"}


def main() -> int:
    for path in SCHEMA_PATHS:
        if not path.exists():
            print(f"ERROR: missing {path.relative_to(ROOT)}")
            return 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid JSON in {path.relative_to(ROOT)}: {exc}")
            return 1
        missing = sorted(REQUIRED_KEYS - set(data))
        if missing:
            print(f"ERROR: {path.relative_to(ROOT)} missing keys {missing}")
            return 1
        if data.get("type") != "object":
            print(f"ERROR: {path.relative_to(ROOT)} type must be object")
            return 1
        print(f"OK: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
