#!/usr/bin/env python3
"""Convert `cargo metadata --format-version 1` output into a compact SPDX-like SBOM.

This helper intentionally avoids network access and external dependencies. It is not a
full SPDX implementation. It emits a deterministic JSON document with the SPDX fields
needed for NLBoot operator-test release evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def package_external_ref(package: dict[str, Any]) -> list[dict[str, str]]:
    checksum = package.get("checksum")
    if not checksum:
        return []
    return [
        {
            "referenceCategory": "PACKAGE-MANAGER",
            "referenceType": "purl",
            "referenceLocator": f"pkg:cargo/{package['name']}@{package['version']}?checksum={checksum}",
        }
    ]


def package_to_spdx(package: dict[str, Any]) -> dict[str, Any]:
    name = package["name"]
    version = package.get("version", "UNKNOWN")
    package_id = f"SPDXRef-Package-{name.replace('_', '-').replace('.', '-')}-{version.replace('.', '-')}"
    source = package.get("source") or "NOASSERTION"
    license_value = package.get("license") or "NOASSERTION"
    return {
        "SPDXID": package_id,
        "name": name,
        "versionInfo": version,
        "downloadLocation": source,
        "filesAnalyzed": False,
        "licenseConcluded": license_value,
        "licenseDeclared": license_value,
        "copyrightText": "NOASSERTION",
        "externalRefs": package_external_ref(package),
    }


def build_sbom(metadata: dict[str, Any], document_name: str) -> dict[str, Any]:
    packages = [package_to_spdx(package) for package in metadata.get("packages", [])]
    root_package_ids = set()
    for root in metadata.get("workspace_members", []):
        for package in metadata.get("packages", []):
            if package.get("id") == root:
                name = package["name"]
                version = package.get("version", "UNKNOWN")
                root_package_ids.add(
                    f"SPDXRef-Package-{name.replace('_', '-').replace('.', '-')}-{version.replace('.', '-')}"
                )
    relationships = []
    for root_id in sorted(root_package_ids):
        for package in packages:
            if package["SPDXID"] != root_id:
                relationships.append(
                    {
                        "spdxElementId": root_id,
                        "relationshipType": "DEPENDS_ON",
                        "relatedSpdxElement": package["SPDXID"],
                    }
                )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": document_name,
        "documentNamespace": f"https://sourceos.local/sbom/{document_name}",
        "creationInfo": {
            "creators": ["Tool: nlboot cargo_metadata_to_spdx.py"],
            "created": "1970-01-01T00:00:00Z",
            "comment": "Deterministic operator-test SBOM generated from cargo metadata.",
        },
        "packages": packages,
        "relationships": relationships,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path, help="Path to cargo metadata JSON")
    parser.add_argument("output", type=Path, help="Path to output SPDX JSON")
    parser.add_argument("--document-name", default="nlboot-client-sbom", help="SPDX document name")
    args = parser.parse_args()

    metadata = load_json(args.metadata)
    sbom = build_sbom(metadata, args.document_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
