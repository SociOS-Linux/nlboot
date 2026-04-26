from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_cli_examples_emit_safe_recovery_plan():
    root = repo_root()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "nlboot.cli",
            "--manifest",
            str(root / "examples" / "signed_boot_manifest.recovery.json"),
            "--token",
            str(root / "examples" / "enrollment_token.recovery.json"),
            "--trusted-keys",
            str(root / "examples" / "trusted_keys.recovery.json"),
            "--require-fips",
            "--now",
            "2026-04-26T14:35:00Z",
        ],
        cwd=root,
        env={"PYTHONPATH": str(root / "src")},
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    plan = payload["plan"]
    assert plan["action"] == "boot-recovery"
    assert plan["execute"] is False
    assert plan["boot_release_set_id"] == "urn:srcos:boot-release-set:m2-demo-recovery-2026-04-26"
    assert plan["release_set_ref"] == "urn:srcos:release-set:m2-demo-2026-04-26"
    assert plan["signature_algorithm"] == "rsa-pss-sha256"
    assert plan["crypto_profile"] == "fips-140-3-compatible"
