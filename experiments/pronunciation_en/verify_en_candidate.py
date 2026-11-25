#!/usr/bin/env python3
"""Verify an experimental EN candidate from untrusted local files without publishing."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from build_en_candidate import EXPECTED_SCORING_FILES, EXTRA_LEXICONS, REVISION, digest_file

FILE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,120}$")


def verify(candidate: Path) -> dict:
    root = candidate.resolve()
    data = json.loads((root / "candidate_inventory.json").read_text("utf-8"))
    if data.get("status") != "not_for_release" or data.get("upstream_commit") != REVISION:
        raise ValueError("Not an approved experimental candidate")
    gates = data.get("gates")
    if not isinstance(gates, dict) or any(value is not False for value in gates.values()):
        raise ValueError("Experimental candidate was altered to claim release readiness")
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("Candidate assets are missing")
    expected = EXPECTED_SCORING_FILES | set(EXTRA_LEXICONS)
    if len(assets) != len(expected):
        raise ValueError("Wrong number of English assets")
    seen = set()
    for row in assets:
        original = row.get("original_path")
        flat = row.get("asset_name")
        if original not in expected or not isinstance(flat, str) or not FILE.fullmatch(flat):
            raise ValueError("Unknown or unsafe candidate resource")
        if flat != original.replace("/", "__"):
            raise ValueError("Unexpected runtime path flattening")
        if original in seen:
            raise ValueError("Duplicated resource")
        seen.add(original)
        file = root / "assets" / flat
        if file.is_symlink() or not file.is_file():
            raise ValueError(f"Missing or symlinked resource {original}")
        size, sha = digest_file(file)
        if size != row.get("bytes") or sha != row.get("sha256"):
            raise ValueError(f"SHA-256 or byte size mismatch: {original}")
    if seen != expected:
        raise ValueError("Incomplete English resources")
    extra = {
        p.name for p in (root / "assets").iterdir()
        if p.is_file()
    } - {row["asset_name"] for row in assets}
    if extra:
        raise ValueError(f"Unexpected unreviewed asset files: {sorted(extra)}")
    unresolved = set(data.get("license_issues_to_resolve", []))
    if not {"prosody/stress_v3.json", "prosody/stress_v3.onnx"}.issubset(unresolved):
        raise ValueError("Known upstream share-alike uncertainty must remain visible")
    return {"files": len(seen), "total_bytes": sum(row["bytes"] for row in assets),
            "license_issues_to_resolve": sorted(unresolved),
            "release_ready": False, "on_device_tested": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, required=True)
    args = ap.parse_args()
    try:
        result = verify(args.candidate)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        ap.exit(2, f"Candidate integrity verification failed: {e}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
