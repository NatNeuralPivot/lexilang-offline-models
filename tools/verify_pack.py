#!/usr/bin/env python3
"""Verify a staged/downloaded Lexi offline pack without internet dependencies."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO = "NatNeuralPivot/lexilang-offline-models"
NAME = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]{0,99}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 2_000_000_000


def verify(manifest_path, assets_dir):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    for field in ("id", "version"):
        value = manifest.get(field)
        if not isinstance(value, str) or not NAME.fullmatch(value) or value in (".", ".."):
            raise ValueError(f"Invalid {field}")
    for field in ("license", "notice"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            raise ValueError(f"Missing {field}")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("No assets")
    seen = set()
    for entry in assets:
        if not isinstance(entry, dict) or set(entry) != {"name", "downloadURL", "bytes", "sha256"}:
            raise ValueError("Unexpected manifest asset fields")
        name = entry["name"]
        if not isinstance(name, str) or not NAME.fullmatch(name) or name in (".", ".."):
            raise ValueError("Unsafe asset filename")
        if name in seen:
            raise ValueError("Duplicate filename: " + name)
        seen.add(name)
        size = entry["bytes"]
        digest = entry["sha256"]
        if type(size) is not int or not (0 < size <= MAX_BYTES):
            raise ValueError("Invalid file size")
        if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
            raise ValueError("Invalid SHA256 checksum")
        url = urlsplit(entry["downloadURL"])
        prefix = "/" + REPO + "/releases/download/"
        if (url.scheme != "https" or url.hostname != "github.com" or url.username
                or url.password or url.query or url.fragment
                or not url.path.startswith(prefix) or not url.path.endswith("/" + name)):
            raise ValueError("Wrong release URL: " + name)
        path = assets_dir / name
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or symlinked asset: " + name)
        actual_size = 0
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                actual_size += len(block)
                h.update(block)
        if actual_size != size:
            raise ValueError("Size mismatch: " + name)
        if h.hexdigest() != digest:
            raise ValueError("SHA256 mismatch: " + name)
    if not {"NOTICE.txt", "PROVENANCE.json", "LICENSES.txt"}.issubset(seen):
        raise ValueError("Required notices or provenance missing from pack")
    return len(assets)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--assets-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        n = verify(args.manifest, args.assets_dir)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Verification failed: {exc}\n")
    print(f"Verified {n} complete files, SHA256 + sizes + public release URL contract")


if __name__ == "__main__":
    main()
