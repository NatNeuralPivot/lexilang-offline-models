#!/usr/bin/env python3
"""Stage a complete, license-reviewed Lexi assessment pack for GitHub Releases.

Python >=3.9, standard library only. Does not upload/publish anything.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO = "NatNeuralPivot/lexilang-offline-models"
MAX_BYTES = 2_000_000_000  # Below GitHub's per-release-file limit.
SAFE = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9._-]{0,99}$")
RESERVED = {"NOTICE.txt", "PROVENANCE.json", "pack.json", "SHA256SUMS"}
BAD_LICENSES = {"", "unknown", "unspecified", "tbd", "none"}


def validate_name(value, field):
    if not isinstance(value, str) or not SAFE.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"Unsafe {field}: {value!r}")
    return value


def https_url(value, field):
    if not isinstance(value, str):
        raise ValueError(f"Missing {field}")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError(f"{field} must be a public HTTPS link")
    return value


def sha256_and_size(path):
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            n += len(block)
            if n > MAX_BYTES:
                raise ValueError(f"Asset exceeds safe 2 GB limit: {path.name}")
            h.update(block)
    if n == 0:
        raise ValueError(f"Asset is empty: {path.name}")
    return n, h.hexdigest()


def stage_asset(path, destination):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or symlinked asset: {path}")
    size, digest = sha256_and_size(path)
    shutil.copyfile(path, destination)
    staged_size, staged_digest = sha256_and_size(destination)
    if (size, digest) != (staged_size, staged_digest):
        raise ValueError(f"Asset changed during staging: {path.name}")
    return size, digest


def prepare(spec, assets_dir, output_root):
    if not isinstance(spec, dict):
        raise ValueError("Pack specification must be an object")
    pack_id = validate_name(spec.get("id"), "pack id")
    version = validate_name(spec.get("version"), "version")
    tag = validate_name(spec.get("releaseTag"), "release tag")
    license_id = spec.get("license")
    notice = spec.get("notice")
    if not isinstance(license_id, str) or license_id.strip().lower() in BAD_LICENSES:
        raise ValueError("Pack license must describe redistributable licensing")
    if not isinstance(notice, str) or len(notice.strip()) < 3:
        raise ValueError("Pack notice is required")
    sources = spec.get("assets")
    if not isinstance(sources, list) or not sources:
        raise ValueError("Pack must contain real assets")

    # Validate EVERYTHING before touching output. No absolute paths or traversal.
    names = set()
    for item in sources:
        if not isinstance(item, dict):
            raise ValueError("Asset metadata must be an object")
        name = validate_name(item.get("name"), "asset name")
        if name in RESERVED or name in names:
            raise ValueError(f"Reserved or duplicate asset name: {name}")
        names.add(name)
        if item.get("redistributionApproved") is not True or item.get("reviewed") is not True:
            raise ValueError(f"Legal review missing for {name}")
        if not isinstance(item.get("reviewedBy"), str) or not item["reviewedBy"].strip():
            raise ValueError(f"Reviewer not recorded for {name}")
        license_name = item.get("license")
        if not isinstance(license_name, str) or license_name.strip().lower() in BAD_LICENSES:
            raise ValueError(f"Missing exact license for {name}")
        https_url(item.get("sourceURL"), "sourceURL")
        https_url(item.get("reviewEvidence"), "reviewEvidence")
        asset_path = assets_dir / name
        if asset_path.is_symlink() or not asset_path.is_file():
            raise ValueError(f"Asset unavailable or is a symlink: {name}")
        if asset_path.stat().st_size <= 0 or asset_path.stat().st_size > MAX_BYTES:
            raise ValueError(f"Invalid asset size: {name}")

    if "LICENSES.txt" not in names:
        raise ValueError("Include a reviewed LICENSES.txt with required full license texts and attributions")

    root = output_root / pack_id / version
    if root.exists():
        raise FileExistsError(f"Destination already exists: {root}; versions are immutable")
    root.mkdir(parents=True)
    prefix = f"https://github.com/{REPO}/releases/download/{tag}/"
    manifest = {"id": pack_id, "version": version, "license": license_id,
                "notice": notice, "assets": []}
    evidence = {"packId": pack_id, "version": version, "releaseTag": tag,
                "reviewedAssets": sources}
    notice_lines = [
        f"Lexi Lang offline assessment assets - {pack_id} {version}",
        notice, "",
        "See LICENSES.txt for full license texts and required attribution.",
        "Third-party source and review provenance follows:", ""
    ]
    for item in sources:
        notice_lines.append(
            f"{item['name']} | {item['license']} | {item['sourceURL']} | review {item['reviewEvidence']}"
        )

    (root / "NOTICE.txt").write_text("\n".join(notice_lines) + "\n", encoding="utf-8")
    (root / "PROVENANCE.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for item in sources:
        stage_asset(assets_dir / item["name"], root / item["name"])

    for name in sorted(names | {"NOTICE.txt", "PROVENANCE.json"}):
        size, digest = sha256_and_size(root / name)
        manifest["assets"].append({
            "name": name, "downloadURL": prefix + name,
            "bytes": size, "sha256": digest
        })
    (root / "pack.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (root / "SHA256SUMS").write_text(
        "".join(a["sha256"] + "  " + a["name"] + "\n" for a in manifest["assets"]),
        encoding="utf-8"
    )
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True, help="Local reviewed pack specification JSON")
    parser.add_argument("--assets-dir", type=Path, required=True, help="Directory with real model assets + LICENSES.txt")
    parser.add_argument("--output-root", type=Path, default=Path("dist"), help="Output staging directory")
    args = parser.parse_args(argv)
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        staged = prepare(spec, args.assets_dir, args.output_root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Cannot prepare pack: {error}\n")
    print(f"Prepared, NOT published: {staged}")
    print("Verify locally, benchmark on devices, upload via GitHub Releases, THEN update packs.json.")


if __name__ == "__main__":
    main()
