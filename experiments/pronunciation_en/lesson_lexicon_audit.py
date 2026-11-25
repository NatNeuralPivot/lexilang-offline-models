#!/usr/bin/env python3
"""Audit EN phoneme lexicon coverage on actual Lexi Lang lesson prompts.

This is NOT a pronunciation-quality score or full G2P/inflection test.
No learner data is read. The private lesson JSON stays on the local computer.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")
LEVELS = {"A0", "A1", "A2", "B1", "B2", "C1", "C2"}


def read_english_lexicon(gzip_path: Path) -> set[str]:
    keys = set()
    with gzip.open(gzip_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("#"):
                continue
            token = line.partition("\t")[0].strip()
            if token:
                keys.add(token.lower())
    if not keys:
        raise ValueError("Empty lexicon")
    return keys


def collect_prompts(payload) -> list[tuple[str, str]]:
    """Accept LexiCurriculum lesson arrays, with no modification of source."""
    if not isinstance(payload, dict):
        raise ValueError("Expected a LexiCurriculum JSON object")
    rows = payload.get("items", [])
    if not isinstance(rows, list):
        raise ValueError("Expected items[] in lesson JSON")
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        level = row.get("cefr") or row.get("level") or "unknown"
        text = row.get("prompt_en") or row.get("promptEn") or ""
        if isinstance(text, str) and isinstance(level, str) and text.strip():
            result.append((level.upper(), text))
    return result


def coverage(lexicon: set[str], prompts: list[tuple[str, str]]) -> dict:
    per_level = {}
    for level, text in prompts:
        if level not in LEVELS:
            continue
        bucket = per_level.setdefault(level, {"all": Counter(), "unknown": Counter(), "prompts": 0})
        bucket["prompts"] += 1
        for match in WORD.finditer(text):
            word = match.group(0).lower().replace("’", "'")
            bucket["all"][word] += 1
            if word not in lexicon:
                bucket["unknown"][word] += 1
    result = {}
    for level in sorted(per_level):
        row = per_level[level]
        total = sum(row["all"].values())
        outside = sum(row["unknown"].values())
        result[level] = {
            "prompts": row["prompts"],
            "token_occurrences": total,
            "in_lexicon_occurrences": total - outside,
            "lexicon_coverage_fraction": round((total - outside) / total, 5) if total else None,
            "distinct_OOV_words": len(row["unknown"]),
            "top_OOV": [name for name, _ in row["unknown"].most_common(30)],
        }
    return {
        "status": "lexicon_coverage_not_pronunciation_accuracy",
        "method": "exact English word keys in upstream CMUdict-derived lexicon; no G2P fallback included",
        "levels": result,
        "warning": "Prompt instructions and names are included; unknown words may still be handled by upstream LTS. This is NOT phoneme scoring.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--lessons-json", type=Path, nargs="+", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    try:
        lexicon = read_english_lexicon(args.candidate / "assets" / "lex__en.tsv.gz")
        prompts = []
        for p in args.lessons_json:
            prompts.extend(collect_prompts(json.loads(p.read_text("utf-8"))))
        report = coverage(lexicon, prompts)
        if args.out.exists():
            raise FileExistsError(f"Refusing to overwrite {args.out}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print(f"Audited {len(prompts)} English prompts; output: {args.out}")
        for level, row in report["levels"].items():
            print(level, f"{row['lexicon_coverage_fraction']:.1%} exact dictionary coverage,"
                         f" {row['distinct_OOV_words']} distinct unknown words")
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        ap.exit(2, f"Coverage audit rejected: {error}\n")


if __name__ == "__main__":
    main()
