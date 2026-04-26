from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .protocol import EnrollmentToken, NlbootError, SignedBootManifest, build_boot_plan


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise NlbootError(f"expected JSON object in {path}")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a safe nlboot plan from a signed manifest and enrollment token")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--now", help="Optional ISO-8601 override for tests")
    args = parser.parse_args(argv)

    try:
        now = datetime.fromisoformat(args.now.replace("Z", "+00:00")).astimezone(timezone.utc) if args.now else None
        manifest = SignedBootManifest.from_dict(load_json(args.manifest))
        token = EnrollmentToken.from_dict(load_json(args.token))
        plan = build_boot_plan(manifest, token, now=now)
    except (NlbootError, ValueError, json.JSONDecodeError) as exc:
        print(f"nlboot-plan: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"ok": True, "plan": plan.to_dict()}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
