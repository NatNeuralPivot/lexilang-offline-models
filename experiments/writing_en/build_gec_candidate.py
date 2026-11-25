#!/usr/bin/env python3
"""Download one complete English GECToR candidate from a PINNED HF revision.

This is NOT a model installer for Lexi Lang and does NOT upload any weights.
The output is an unapproved, locally staged model candidate for Mac testing.
Requires: pip install huggingface_hub
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

MODEL_ID = "deepquillapp/gector-grammar"
REQUIRED = ("model.onnx", "tokenizer.json", "labels.json", "verb-form-vocab.txt")
MAX_TOTAL = 1_300_000_000
MAX_FILE = 1_100_000_000
REVISION = re.compile(r"^[0-9a-f]{40}$")


def sha256(path: Path):
    total = 0
    h = hashlib.sha256()
    with path.open("rb") as file:
        for buf in iter(lambda: file.read(1024 * 1024), b""):
            total += len(buf)
            if total > MAX_FILE:
                raise ValueError(f"File larger than safety limit: {path.name}")
            h.update(buf)
    if total < 8:
        raise ValueError(f"File too small to be a real artifact: {path.name}")
    return total, h.hexdigest()


def check_metadata(metadata: dict) -> None:
    if set(metadata) != {"revision", "license", "files", "source"}:
        raise ValueError("Unexpected model metadata fields")
    if not REVISION.fullmatch(metadata["revision"]):
        raise ValueError("Model revision must be an exact 40-char commit SHA")
    if metadata["source"] != MODEL_ID or metadata["license"] != "apache-2.0":
        raise ValueError("Unreviewed upstream model or license")
    if set(metadata["files"]) != set(REQUIRED):
        raise ValueError("Missing or unexpected required model file")


def check_model_files(root: Path) -> dict:
    data = root / "assets"
    inv = {}
    for name in REQUIRED:
        file = data / name
        if not file.is_file() or file.is_symlink():
            raise ValueError(f"Missing/symlinked model dependency: {name}")
        size, digest = sha256(file)
        if name == "model.onnx" and size < 20_000_000:
            raise ValueError("ONNX appears truncated: suspiciously small")
        if name.endswith(".json"):
            structure = json.loads(file.read_text("utf-8"))
            if not isinstance(structure, dict) or not structure:
                raise ValueError(f"Invalid model JSON: {name}")
        inv[name] = {"bytes": size, "sha256": digest}
    if sum(i["bytes"] for i in inv.values()) > MAX_TOTAL:
        raise ValueError("Model candidate exceeds safety budget")
    return inv


def assemble(source: Path, output: Path, metadata: dict) -> dict:
    """Assemble from a predownloaded snapshot to permit deterministic offline tests."""
    check_metadata(metadata)
    if output.exists():
        raise FileExistsError("Will not overwrite a staged candidate")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".lexi-writing-", dir=str(output.parent)))
    try:
        assets = staging / "assets"
        assets.mkdir()
        for name in REQUIRED:
            f = source / name
            if not f.is_file():
                raise FileNotFoundError(f"Missing source artifact {name}")
            shutil.copyfile(f, assets / name)
        files = check_model_files(staging)
        for name, details in files.items():
            original = metadata["files"][name]
            if not isinstance(original, dict):
                raise ValueError(f"Bad upstream descriptor for {name}")
            upstream_size = original.get("bytes")
            upstream_sha = original.get("sha256")
            if upstream_size is not None and upstream_size != details["bytes"]:
                raise ValueError(f"Upstream file size mismatch: {name}")
            if upstream_sha is not None and upstream_sha != details["sha256"]:
                raise ValueError(f"Upstream SHA-256 mismatch: {name}")
        record = {
            "schema_version": 1, "id": "lexi-writing-gec-deepquill",
            "model_kind": "english_grammar_edit_tagger",
            "status": "research_candidate_not_release_ready",
            "source": MODEL_ID, "revision": metadata["revision"],
            "license_declared": metadata["license"],
            "assets": files,
            "gates": {
                "licensing_provenance_approved": False,
                "macos_onnx_inference_passed": False,
                "iphone_onnx_inference_passed": False,
                "gec_quality_benchmark_passed": False,
                "utf16_offset_accuracy_passed": False,
                "russian_spanish_explanations_passed": False,
                "no_auto_replace_in_original_draft": True
            },
            "notes": [
                "Model score does not certify English CEFR proficiency.",
                "LanguageTool, speech recognition and WordNet are NOT substitutes for this GEC model.",
                "Model remains separate from the public packs.json release registry.",
                "Do not publish or enable until legal audit + offline Apple QA passes."
            ]
        }
        (staging / "candidate_inventory.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        staging.rename(output)
        return record
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def fetch_hf_snapshot(destination: Path, pinned_revision: str | None) -> dict:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        raise RuntimeError("Install only the official Python package: pip install huggingface_hub")
    api = HfApi()
    info = api.model_info(MODEL_ID, revision=pinned_revision or "main", files_metadata=True)
    commit = info.sha
    if not REVISION.fullmatch(commit):
        raise ValueError("Hugging Face did not return a precise immutable commit SHA")
    if pinned_revision is not None and commit != pinned_revision:
        raise ValueError("Resolved model revision differs from explicit pinned SHA")
    card = getattr(info, "card_data", None)
    license_id = getattr(card, "license", None) if card is not None else None
    if license_id != "apache-2.0":
        raise ValueError(f"Model card license changed/unverified: {license_id}")
    siblings = {x.rfilename: x for x in info.siblings}
    if not set(REQUIRED).issubset(siblings):
        raise ValueError("Upstream model dependencies changed")
    inventory = {}
    downloaded = {}
    destination.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED:
        sibling = siblings[name]
        # HF can expose either lfs.sha256 or Xet metadata. When an authoritative
        # upstream digest is absent, we record an audit BLOCKER, never fabricate it.
        lfs = getattr(sibling, "lfs", None)
        digest = lfs.get("sha256") if isinstance(lfs, dict) else None
        size = sibling.size if isinstance(sibling.size, int) and sibling.size > 0 else None
        if size is not None and size > MAX_FILE:
            raise ValueError(f"Upstream artifact too large: {name}")
        actual = Path(hf_hub_download(
            repo_id=MODEL_ID, revision=commit, filename=name,
            local_dir=str(destination)
        ))
        if actual.is_symlink():
            raise ValueError(f"Refusing a symlinked downloaded artifact: {name}")
        n, sha = sha256(actual)
        if size is not None and size != n:
            raise ValueError(f"Download size mismatch: {name}")
        if digest is not None and digest != sha:
            raise ValueError(f"Download digest mismatch: {name}")
        inventory[name] = {"bytes": size, "sha256": digest}
        downloaded[name] = {"bytes": n, "sha256": sha}
    return {"revision": commit, "license": license_id, "files": inventory, "source": MODEL_ID}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--revision", default=None,
                        help="Optional immutable 40-character HF commit; recommended for repeat runs")
    args = parser.parse_args()
    if args.revision is not None and not REVISION.fullmatch(args.revision):
        parser.exit(2, "Invalid --revision SHA\n")
    if args.out.exists():
        parser.exit(2, "Candidate already exists; never overwrite immutable experiment\n")
    try:
        with tempfile.TemporaryDirectory(prefix="lexi-hf-writing-") as temp:
            downloaded = Path(temp)
            metadata = fetch_hf_snapshot(downloaded, args.revision)
            record = assemble(downloaded, args.out, metadata)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        parser.exit(2, f"Writing model staging failed: {error}\n")
    print("Experimental GEC model staged, NOT installed in Lexi Lang")
    print(f"Upstream pinned revision: {record['revision']}")
    print("Files: " + ", ".join(record["assets"]))
    print("Status: " + record["status"])
    print("No GitHub Release, no packs.json update, no UI changes.")


if __name__ == "__main__":
    main()
