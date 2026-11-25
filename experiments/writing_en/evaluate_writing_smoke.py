#!/usr/bin/env python3
"""Fail-closed smoke evaluation of ACTUAL GEC edit outputs (never fake inference).

Input model output JSONL from a real local ONNX runner:
{"id":"A1-001","original":"She go to school every day.","revised_text":"She goes to school every day."}

This does not assess essay-level CEFR, grammar precision or fluency.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def rows(path: Path):
    results = []
    with path.open("r", encoding="utf-8") as input_file:
        for index, line in enumerate(input_file, 1):
            if not line.strip(): continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"Row {index} is not an object")
            results.append(record)
    return results


def evaluate(cases: list[dict], predictions: list[dict]) -> dict:
    cases_by_id = {row["id"]: row for row in cases}
    if len(cases_by_id) != len(cases):
        raise ValueError("Duplicate test case IDs")
    prediction_ids = [p.get("id") for p in predictions]
    if len(set(prediction_ids)) != len(prediction_ids):
        raise ValueError("Duplicate prediction IDs")
    if set(prediction_ids) != set(cases_by_id):
        raise ValueError("Missing or extra predictions (no silent partial pass)")
    positive = negative = detected = preserved = 0
    failures = []
    for p in predictions:
        case = cases_by_id[p["id"]]
        if p.get("original") != case["text"]:
            raise ValueError(f"Source text differs for {p['id']}")
        rewritten = p.get("revised_text")
        if not isinstance(rewritten, str):
            raise ValueError(f"Missing real inferred revised text: {p['id']}")
        changed = rewritten != case["text"]
        if case["type"] == "error":
            positive += 1
            detected += int(changed)
            if not changed: failures.append({"id": p["id"], "reason": "missed_known_error"})
        elif case["type"] == "keep":
            negative += 1
            preserved += int(not changed)
            if changed: failures.append({"id": p["id"], "reason": "changed_valid_text",
                                        "revision": rewritten})
        else:
            raise ValueError(f"Unknown expectation in test case: {p['id']}")
    return {
        "kind": "small_smoke_test_not_production_quality_metric",
        "model_execution_unverified_by_this_script": False,
        "observations_from_supplied_outputs_only": len(predictions),
        "known_error_inputs": positive, "errors_causing_a_change": detected,
        "valid_inputs": negative, "valid_inputs_preserved": preserved,
        "failures": failures,
        "warning": ("A changed error sentence may be corrected WRONG. Review every change "
                    "manually. This check is NOT grammar precision/recall or a CEFR grade.")
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", type=Path, default=Path(__file__).with_name("writing_smoke_cases.jsonl"))
    ap.add_argument("--actual-predictions", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    try:
        if args.report.exists():
            raise FileExistsError("Refusing to overwrite QA evidence")
        report = evaluate(rows(args.cases), rows(args.actual_predictions))
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        ap.exit(2, f"Writing QA blocked: {e}\n")
    print(f"Scored {len(report['failures'])} failure cases from ACTUAL predictions")
    print("Manual human judgement required before any model release.")


if __name__ == "__main__":
    main()
