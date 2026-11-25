#!/usr/bin/env python3
"""Reproduce an isolated English lexicon/calibration *candidate*, never a release.

Input: a locally cloned, pinned upstream moglearn/pronunciada checkout.
No network, model inference, external Python dependencies, publication, or Git changes.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

UPSTREAM = "moglearn/pronunciada"
REVISION = "4619a298e5e2de927120122585683d18eda1f7c4"
EXTRA_LEXICONS = ("lex/en.tsv.gz", "lex/en_lts.tsv.gz")
# One exhaustive runtime-traced EN dependency inventory in LICENSES_SHIPPED.json.
# Future upstream changes must be audited rather than silently inherited.
EXPECTED_SCORING_FILES = {
    "calib/config.json", "calib/contrast_caps.json", "calib/omission.json",
    "calib/phone_dist.npz", "calib/sound_U.npz", "calib/word.npz",
    "calib/word_reg.npz", "calib/word_reg_r6.npz",
    "coach/contrast_heads.json", "zipa_tokens.txt",
    "adapters/en.npz", "native/en.json", "calib/prosody/en.json",
    "calib/sentence_r19.npz", "calib/seqhead_en.npz", "calib/seqhead_en.onnx",
    "calib/sound_B.npz", "calib/sound_E.npz", "calib/sound_E_emb.npz",
    "prosody/stress_v3.json", "prosody/stress_v3.zemb.npz",
    "prosody/stress_v3.onnx"
}
VALID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
MAX_FILE_BYTES = 100_000_000  # No full ZIPA ONNX weights in this candidate!


def digest_file(path: Path) -> tuple[int, str]:
    total = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(block)
            if total > MAX_FILE_BYTES:
                raise ValueError(f"Unexpected huge resource: {path.name}")
            digest.update(block)
    if total == 0:
        raise ValueError(f"Empty resource: {path.name}")
    return total, digest.hexdigest()


def upstream_commit(checkout: Path) -> str:
    p = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                       capture_output=True, text=True, check=True)
    return p.stdout.strip()


def check_dictionary(path: Path, min_entries: int = 1000) -> dict:
    if path.suffix != ".gz":
        raise ValueError("Not a gzip dictionary")
    entries, duplicates, variants, metadata, stressed, previous = 0, 0, 0, 0, 0, ""
    words = set()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for line in source:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                metadata += 1
                continue
            cells = line.split("\t")
            word, pronunciations = cells[0], cells[1:]
            if not word or not pronunciations or any(not p.strip() for p in pronunciations):
                raise ValueError(f"Malformed pronunciation entry near row {entries + 1}")
            if previous and word < previous:
                raise ValueError("Dictionary not sorted as expected by upstream SortedLexicon")
            if word in words:
                duplicates += 1
                raise ValueError(f"Duplicate dictionary key {word!r}")
            words.add(word)
            previous = word
            for pron in pronunciations:
                toks = pron.split(" ")
                if any(not t or "\n" in t for t in toks):
                    raise ValueError(f"Invalid phone sequence for {word!r}")
                if any(t[-1:] in ("0", "1", "2") for t in toks):
                    stressed += 1
            entries += 1
            variants += len(pronunciations)
    if entries < min_entries:
        raise ValueError(f"Dictionary too small: {entries} entries")
    return {
        "entries": entries, "pronunciations": variants,
        "variants_above_primary": variants - entries,
        "with_stress_marked_pronunciations": stressed,
        "metadata_lines": metadata, "duplicate_keys": duplicates,
    }


def check_numeric_json(path: Path):
    def inspect(value):
        if isinstance(value, dict):
            for x in value.values():
                inspect(x)
        elif isinstance(value, list):
            for x in value:
                inspect(x)
        elif isinstance(value, float):
            import math
            if not math.isfinite(value):
                raise ValueError(f"Non-finite calibration coefficient in {path}")
    data = json.loads(path.read_text("utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError(f"Invalid calibration JSON {path}")
    inspect(data)


def check_npz(path: Path):
    # Treat .npz as ZIP without extracting. No pickle or executable resources.
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if not entries or len(entries) > 2000:
            raise ValueError(f"Invalid NPZ entries in {path}")
        for member in entries:
            if not member.filename.endswith(".npy"):
                raise ValueError(f"Unexpected NPZ member: {member.filename}")
            if member.file_size > MAX_FILE_BYTES:
                raise ValueError(f"NPZ member too large: {member.filename}")


def build(checkout: Path, output: Path, min_entries: int = 1000) -> dict:
    checkout = checkout.resolve()
    output = output.resolve()
    if upstream_commit(checkout) != REVISION:
        raise ValueError(f"Unapproved upstream revision: requires {REVISION}")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite immutable experiment: {output}")
    source = checkout / "pronunciada" / "data"
    audit_path = source / "LICENSES_SHIPPED.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    records = audit.get("en")
    if not isinstance(records, list):
        raise ValueError("Upstream English file inventory missing")
    paths = [row.get("path") for row in records]
    if set(paths) != EXPECTED_SCORING_FILES or len(paths) != len(EXPECTED_SCORING_FILES):
        raise ValueError("Upstream EN scoring inventory changed. Re-audit before updating")
    if any(row.get("licence", "").lower() in ("", "unknown", "unlisted") for row in records):
        raise ValueError("Upstream inventory contains unlicensed resources")

    # Never overwrite an existing release/candidate. Stage transactionally.
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".lexi-en-", dir=output.parent))
    try:
        assets = staging / "assets"
        assets.mkdir()
        inventory, unresolved = [], []
        legal = {row["path"]: row for row in records}
        for rel in sorted(EXPECTED_SCORING_FILES | set(EXTRA_LEXICONS)):
            path = Path(rel)
            if ".." in path.parts or path.is_absolute():
                raise ValueError("Path traversal in upstream metadata")
            original = source / path
            if original.is_symlink() or not original.is_file():
                raise FileNotFoundError(f"Missing upstream resource {rel}")
            flat = rel.replace("/", "__")
            if not VALID.fullmatch(flat):
                raise ValueError(f"Invalid flat asset name: {flat}")
            size, sha = digest_file(original)
            if flat.endswith(".npz"):
                check_npz(original)
            elif flat.endswith(".json"):
                check_numeric_json(original)
            elif flat.endswith(".gz"):
                if rel == "lex/en.tsv.gz":
                    lex_stats = check_dictionary(original, min_entries=min_entries)
                else:
                    with gzip.open(original, "rb") as stream:
                        if not stream.read(16):
                            raise ValueError(f"Empty gz: {rel}")
            shutil.copyfile(original, assets / flat)
            if digest_file(assets / flat) != (size, sha):
                raise ValueError(f"Copy corrupted: {rel}")
            row = legal.get(rel, {})
            if rel in EXTRA_LEXICONS:
                licence = "BSD-2-Clause-style (CMUdict; attribution required)"
                provenance = "CMUdict -> pronunciada English lexicon"
            else:
                licence = row["licence"]
                provenance = row.get("source", "")
                if row.get("share_alike_question"):
                    unresolved.append(rel)
            inventory.append({
                "original_path": rel, "asset_name": flat, "bytes": size,
                "sha256": sha, "license": licence, "source": provenance,
                "upstream_commit": REVISION,
            })
        output_data = {
            "schema_version": 1, "kind": "english_assessment_resources_candidate",
            "status": "not_for_release", "upstream": UPSTREAM,
            "upstream_commit": REVISION,
            "license_issues_to_resolve": unresolved,
            "gates": {
                "redistribution_approved": False,
                "acoustic_backbone_present": False,
                "on_device_parity_verified": False,
                "human_rater_calibration_verified": False,
                "source_license_reviewed": False,
            },
            "lexicon_stats": lex_stats, "runtime_paths": {
                row["original_path"]: row["asset_name"] for row in inventory
            },
            "assets": inventory,
        }
        (staging / "candidate_inventory.json").write_text(
            json.dumps(output_data, indent=2, ensure_ascii=False) + "\n", "utf-8")
        staging.rename(output)
        return output_data
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pronunciada", type=Path, required=True,
                   help="Local upstream checkout pinned to REVISION")
    p.add_argument("--out", type=Path, required=True,
                   help="Fresh output directory OUTSIDE any Git repository")
    args = p.parse_args()
    try:
        candidate = build(args.pronunciada, args.out)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError,
            json.JSONDecodeError, zipfile.BadZipFile) as error:
        p.exit(2, f"Candidate build rejected: {error}\n")
    print(f"Prepared {len(candidate['assets'])} validated resource files")
    print(f"EN lexicon: {candidate['lexicon_stats']}")
    print(f"Unresolved licensing: {candidate['license_issues_to_resolve']}")
    print("NOT a release, NOT an iOS model, NOT a pronunciation score.")


if __name__ == "__main__":
    main()
