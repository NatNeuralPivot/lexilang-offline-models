#!/usr/bin/env python3
"""Independently verify an unapproved English-writing GEC download candidate."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from build_gec_candidate import REQUIRED, MODEL_ID, REVISION, check_model_files


def verify(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("Refuse symlinked candidate")
    p = path.resolve()
    manifest = json.loads((p / "candidate_inventory.json").read_text("utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("id") != "lexi-writing-gec-deepquill":
        raise ValueError("Not the expected Lexi GEC experiment")
    if manifest.get("status") != "research_candidate_not_release_ready":
        raise ValueError("Candidate status changed unexpectedly")
    if manifest.get("source") != MODEL_ID or not REVISION.fullmatch(manifest.get("revision", "")):
        raise ValueError("Unpinned/untrusted upstream source")
    if manifest.get("license_declared") != "apache-2.0":
        raise ValueError("Unreviewed declared license")
    gate = manifest.get("gates", {})
    if gate.get("licensing_provenance_approved") is not False or any(
        gate.get(field) is not False for field in
        ("macos_onnx_inference_passed", "iphone_onnx_inference_passed",
         "gec_quality_benchmark_passed", "utf16_offset_accuracy_passed",
         "russian_spanish_explanations_passed")
    ):
        raise ValueError("This research candidate cannot be release-approved automatically")
    if gate.get("no_auto_replace_in_original_draft") is not True:
        raise ValueError("Original draft safety contract missing")
    if not isinstance(manifest.get("assets"), dict) or set(manifest["assets"]) != set(REQUIRED):
        raise ValueError("Candidate file inventory is missing/has extras")
    actual = check_model_files(p)
    for name, values in actual.items():
        if manifest["assets"].get(name) != values:
            raise ValueError(f"Candidate SHA-256/size mismatch: {name}")
    leftovers = {x.name for x in (p / "assets").iterdir()} - set(REQUIRED)
    if leftovers:
        raise ValueError(f"Unlisted candidate assets: {sorted(leftovers)}")
    return {
        "status": "verified_research_bytes_not_a_production_release",
        "revision": manifest["revision"], "files": len(actual),
        "total_bytes": sum(row["bytes"] for row in actual.values()),
        "checksums_ok": True, "runtime_verified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    args = p.parse_args()
    try:
        report = verify(args.candidate)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        p.exit(2, f"Candidate verification failed: {exc}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
