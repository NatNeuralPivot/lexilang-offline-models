#!/usr/bin/env python3
"""Research-only Platt recalibration on HUMAN-LABELLED acoustic evidence.

Never use Apple Speech confidence, transcript edit distance or synthetic
reference speech as pronunciation labels. No "accuracy %" can be published
based on this script alone. Requires speaker-disjoint TRAIN and TEST groups.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

UNITS = {"phone", "word", "sentence", "prosody"}
COLUMNS = {"sample_id", "speaker_id", "split", "unit", "raw_score", "human_accept", "source_engine"}


def clamp(p: float) -> float:
    return min(1 - 1e-6, max(1e-6, p))


def logistic(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


def logit(p: float) -> float:
    p = clamp(p)
    return math.log(p / (1 - p))


def read_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not COLUMNS.issubset(set(reader.fieldnames)):
            raise ValueError("CSV requires: " + ", ".join(sorted(COLUMNS)))
        result = []
        used = set()
        for line, row in enumerate(reader, 2):
            if any(not row.get(key) for key in COLUMNS):
                raise ValueError(f"Missing data on line {line}")
            if row["split"] not in {"train", "test"}:
                raise ValueError(f"Unexpected split on line {line}")
            if row["unit"] not in UNITS:
                raise ValueError(f"Unexpected unit on line {line}")
            if row["human_accept"] not in {"0", "1"}:
                raise ValueError(f"Human labels must be 0 or 1 on line {line}")
            if row["sample_id"] in used:
                raise ValueError(f"Duplicate sample id on line {line}")
            used.add(row["sample_id"])
            try:
                p = float(row["raw_score"])
            except (ValueError, TypeError):
                raise ValueError(f"Invalid raw score on line {line}") from None
            if not math.isfinite(p) or not (0 <= p <= 1):
                raise ValueError(f"Uncalibrated acoustic probability out of range on line {line}")
            result.append({
                "sample_id": row["sample_id"], "speaker_id": row["speaker_id"],
                "split": row["split"], "unit": row["unit"], "score": p,
                "label": int(row["human_accept"]), "source_engine": row["source_engine"],
            })
    return result


def fit_platt(train: list[dict], ridge: float = 0.5) -> tuple[float, float]:
    # Penalised Newton iterations for logit(raw_score) -> P(human accept).
    # Shrinks toward identity (slope 1, intercept 0).
    a, b = 1.0, 0.0
    for _ in range(80):
        g_a = ridge * (a - 1.0)
        g_b = ridge * b
        h_aa = ridge
        h_bb = ridge
        h_ab = 0.0
        for row in train:
            x = logit(row["score"])
            p = logistic(a * x + b)
            delta = p - row["label"]
            w = max(1e-9, p * (1 - p))
            g_a += x * delta
            g_b += delta
            h_aa += w * x * x
            h_ab += w * x
            h_bb += w
        det = h_aa * h_bb - h_ab * h_ab
        if det <= 1e-12:
            raise ValueError("Calibration fit is singular")
        step_a = (h_bb * g_a - h_ab * g_b) / det
        step_b = (h_aa * g_b - h_ab * g_a) / det
        step_a = max(-1.5, min(1.5, step_a))
        step_b = max(-1.5, min(1.5, step_b))
        a -= step_a
        b -= step_b
        if abs(step_a) + abs(step_b) < 1e-7:
            break
    if not math.isfinite(a) or not math.isfinite(b) or a <= 0:
        raise ValueError("Unreliable non-monotonic calibration")
    return a, b


def evaluate(rows: list[dict], a: float, b: float) -> dict:
    n = len(rows)
    if n == 0:
        raise ValueError("No evaluation rows")
    transformed = [clamp(logistic(a * logit(r["score"]) + b)) for r in rows]
    raw = [clamp(r["score"]) for r in rows]
    y = [r["label"] for r in rows]

    def brier(probs):
        return sum((p - k) ** 2 for p, k in zip(probs, y)) / n

    def ece(probs):
        bins = [[] for _ in range(10)]
        for p, truth in zip(probs, y):
            bins[min(9, int(p * 10))].append((p, truth))
        return sum(
            len(group) / n * abs(
                sum(p for p, _ in group) / len(group) -
                sum(t for _, t in group) / len(group)
            ) for group in bins if group
        )

    return {
        "samples": n, "human_positive_rate": sum(y) / n,
        "raw_brier": round(brier(raw), 6),
        "calibrated_brier": round(brier(transformed), 6),
        "raw_ece_10_bins": round(ece(raw), 6),
        "calibrated_ece_10_bins": round(ece(transformed), 6),
    }


def calibrate(rows: list[dict], *,
              min_train: int = 300, min_test: int = 100,
              min_train_speakers: int = 25, min_test_speakers: int = 10) -> dict:
    if not rows:
        raise ValueError("No human-labelled rows")
    units = {r["unit"] for r in rows}
    engines = {r["source_engine"] for r in rows}
    if len(units) != 1 or len(engines) != 1:
        raise ValueError("Mixed units or acoustic models; must calibrate separately")
    engine = next(iter(engines)).lower()
    if any(term in engine for term in ("asr", "apple_speech", "speechrecognition",
                                       "transcript", "edit_distance", "word_error_rate")):
        raise ValueError("ASR/transcript confidence is not an acoustic pronunciation score")
    # Defensive validation also applies to callers not using read_rows().
    if any(not math.isfinite(r["score"]) or not 0 <= r["score"] <= 1 or
           r["label"] not in {0, 1} or r["split"] not in {"train", "test"} for r in rows):
        raise ValueError("Invalid acoustic scores, human labels or split values")
    tr = [r for r in rows if r["split"] == "train"]
    te = [r for r in rows if r["split"] == "test"]
    speakers_tr = {r["speaker_id"] for r in tr}
    speakers_te = {r["speaker_id"] for r in te}
    if speakers_tr & speakers_te:
        raise ValueError("Speaker leakage between training and held-out test")
    if len(tr) < min_train or len(te) < min_test:
        raise ValueError("Not enough human-rated samples")
    if len(speakers_tr) < min_train_speakers or len(speakers_te) < min_test_speakers:
        raise ValueError("Not enough independent speakers")
    if len({r["sample_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate sample IDs")
    if len({r["label"] for r in tr}) != 2 or len({r["label"] for r in te}) != 2:
        raise ValueError("Both human-labelled classes required in each split")

    a, b = fit_platt(tr)
    train_metrics = evaluate(tr, a, b)
    test_metrics = evaluate(te, a, b)
    # A holdout regression cannot be silently promoted to a user-visible score.
    improves = (
        test_metrics["calibrated_brier"] <= test_metrics["raw_brier"] and
        test_metrics["calibrated_ece_10_bins"] <= test_metrics["raw_ece_10_bins"]
    )
    return {
        "schema_version": 1, "kind": "platt_acoustic_calibration_research",
        "status": "research_review_required" if improves else "rejected_holdout_regression",
        "publishable": False,
        "unit": next(iter(units)), "source_engine": next(iter(engines)),
        "features": "logit(raw_acoustic_probability)",
        "coefficients": {"slope": round(a, 9), "intercept": round(b, 9)},
        "speaker_disjoint": True,
        "training_speakers": len(speakers_tr),
        "test_speakers": len(speakers_te),
        "training": train_metrics, "held_out": test_metrics,
        "warnings": [
            "Research only; no automatic substitution for Pronunciada's validated calibration",
            "Human labels must be traceable to original audio and expert annotation",
            "Require test-set separation, subgroup analysis, native iPhone acoustic parity and owner QA",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expert-labelled-csv", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.exit(2, "Refusing to overwrite a calibration experiment\n")
    try:
        report = calibrate(read_rows(args.expert_labelled_csv))
    except (OSError, ValueError) as e:
        parser.exit(2, f"Calibration blocked: {e}\n")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Research calibration recorded: {report['status']}")
    print(f"Held-out Brier {report['held_out']['raw_brier']} -> {report['held_out']['calibrated_brier']}")
    print("NOT shipped, NOT applied to the app or model pack.")


if __name__ == "__main__":
    main()
