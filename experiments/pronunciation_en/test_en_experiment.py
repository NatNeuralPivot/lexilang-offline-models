#!/usr/bin/env python3
"""Synthetic offline fixtures. Never publish generated test bytes as models."""
import csv
import gzip
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_en_candidate import (build, check_dictionary, EXPECTED_SCORING_FILES,
                                REVISION, EXTRA_LEXICONS)
from recalibrate_expert_scores import calibrate, read_rows
from verify_en_candidate import verify
from lesson_lexicon_audit import coverage, collect_prompts


class CandidateBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.checkout = self.home / "upstream"
        self.root = self.checkout / "pronunciada" / "data"
        self.root.mkdir(parents=True)
        self.output = self.home / "candidate"
        files = []
        for name in sorted(EXPECTED_SCORING_FILES):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if name.endswith(".json"):
                target.write_text('{"metadata":"synthetic fixture", "value":[0.25, 1.0]}', "utf-8")
            elif name.endswith(".npz"):
                with zipfile.ZipFile(target, "w") as z:
                    z.writestr("value.npy", b"\x93NUMPY\x01\x00fakefixture")
            else:
                target.write_bytes(b"fixture-not-a-model\n")
            files.append({
                "path": name, "licence": "Apache-2.0",
                "source": "test-only", "share_alike_question": name in {"prosody/stress_v3.json", "prosody/stress_v3.onnx"}
            })
        (self.root / "LICENSES_SHIPPED.json").write_text(json.dumps({"en": files}), "utf-8")
        for name in EXTRA_LEXICONS:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(target, "wt", encoding="utf-8") as f:
                f.write("#onsets\tp t k\napple\tæ1 p ə l\nzoo\tz u1\tz ʊ1\n")

    @patch("build_en_candidate.upstream_commit", return_value=REVISION)
    def test_builds_24_verified_flat_resources(self, _commit):
        inventory = build(self.checkout, self.output, min_entries=2)
        self.assertEqual(len(inventory["assets"]), 24)
        self.assertEqual(inventory["status"], "not_for_release")
        self.assertFalse(inventory["gates"]["acoustic_backbone_present"])
        self.assertFalse(inventory["gates"]["redistribution_approved"])
        self.assertIn("prosody/stress_v3.onnx", inventory["license_issues_to_resolve"])
        self.assertEqual(inventory["lexicon_stats"]["entries"], 2)
        self.assertEqual(verify(self.output)["files"], 24)
        self.assertEqual(inventory["lexicon_stats"]["variants_above_primary"], 1)
        for row in inventory["assets"]:
            self.assertTrue((self.output / "assets" / row["asset_name"]).is_file())
            self.assertNotIn("/", row["asset_name"])

    @patch("build_en_candidate.upstream_commit", return_value=REVISION)
    def test_cannot_overwrite_candidate(self, _commit):
        build(self.checkout, self.output, min_entries=2)
        with self.assertRaises(FileExistsError):
            build(self.checkout, self.output, min_entries=2)

    @patch("build_en_candidate.upstream_commit", return_value="bad")
    def test_wrong_upstream_commit_rejected(self, _commit):
        with self.assertRaisesRegex(ValueError, "Unapproved upstream revision"):
            build(self.checkout, self.output, min_entries=2)
        self.assertFalse(self.output.exists())

    @patch("build_en_candidate.upstream_commit", return_value=REVISION)
    def test_missing_calibration_resource_is_rejected(self, _commit):
        (self.root / "calib" / "sound_U.npz").unlink()
        with self.assertRaises(FileNotFoundError):
            build(self.checkout, self.output, min_entries=2)
        self.assertFalse(self.output.exists())

    @patch("build_en_candidate.upstream_commit", return_value=REVISION)
    def test_upstream_inventory_change_is_blocked(self, _commit):
        p = self.root / "LICENSES_SHIPPED.json"
        data = json.loads(p.read_text())
        data["en"].pop()
        p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "inventory changed"):
            build(self.checkout, self.output, min_entries=2)

    def test_duplicate_unsorted_lexicon_is_rejected(self):
        path = self.home / "bad.tsv.gz"
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write("zoo\tz u1\napple\tæ1 p ə l\n")
        with self.assertRaisesRegex(ValueError, "not sorted"):
            check_dictionary(path, min_entries=2)

    def test_small_lexicon_is_rejected(self):
        path = self.root / EXTRA_LEXICONS[0]
        with self.assertRaisesRegex(ValueError, "too small"):
            check_dictionary(path, min_entries=100)


class ExpertCalibrationTests(unittest.TestCase):
    def samples(self):
        rows = []
        for split, count, speakers in (("train", 100, 10), ("test", 50, 5)):
            for idx in range(count):
                label = (idx // 3) % 2
                # Deliberately miscalibrated: the score looks too certain.
                raw = 0.96 if label else 0.04
                rows.append({
                    "sample_id": f"{split}-{idx}",
                    "speaker_id": f"{split}-speaker-{idx % speakers}",
                    "split": split,
                    "unit": "phone",
                    "score": raw,
                    "label": label,
                    "source_engine": "real-acoustic-scoring-v0"
                })
        return rows

    def test_fit_uses_speaker_disjoint_holdout_and_never_publishes(self):
        report = calibrate(self.samples(), min_train=50, min_test=25,
                           min_train_speakers=8, min_test_speakers=4)
        self.assertEqual(report["unit"], "phone")
        self.assertTrue(report["speaker_disjoint"])
        self.assertFalse(report["publishable"])
        self.assertIn(report["status"], ["research_review_required", "rejected_holdout_regression"])
        self.assertGreater(report["training"]["samples"], report["held_out"]["samples"])

    def test_asr_confidence_is_not_accepted_as_acoustic_calibration(self):
        rows = self.samples()
        for row in rows:
            row["source_engine"] = "Apple_Speech_ASR_confidence"
        with self.assertRaisesRegex(ValueError, "not an acoustic"):
            calibrate(rows, min_train=50, min_test=25,
                      min_train_speakers=8, min_test_speakers=4)

    def test_speaker_leakage_blocks_fitting(self):
        rows = self.samples()
        rows[100]["speaker_id"] = rows[0]["speaker_id"]
        with self.assertRaisesRegex(ValueError, "Speaker leakage"):
            calibrate(rows, min_train=50, min_test=25,
                      min_train_speakers=8, min_test_speakers=4)

    def test_mixed_phone_and_word_scores_block_fitting(self):
        rows = self.samples()
        rows[100]["unit"] = "word"
        with self.assertRaisesRegex(ValueError, "Mixed units"):
            calibrate(rows, min_train=50, min_test=25,
                      min_train_speakers=8, min_test_speakers=4)

    def test_no_human_label_diversity_blocks_fitting(self):
        rows = self.samples()
        for row in rows:
            row["label"] = 1
        with self.assertRaisesRegex(ValueError, "Both human-labelled classes"):
            calibrate(rows, min_train=50, min_test=25,
                      min_train_speakers=8, min_test_speakers=4)

    def test_rejects_asr_or_bad_acoustic_score(self):
        path = Path(self.tempdir()) / "bad.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "sample_id", "speaker_id", "split", "unit",
                "raw_score", "human_accept", "source_engine"
            ])
            writer.writeheader()
            writer.writerow({
                "sample_id": "1", "speaker_id": "s", "split": "train",
                "unit": "phone", "raw_score": "1.2", "human_accept": "1",
                "source_engine": "acoustic-engine"
            })
        with self.assertRaisesRegex(ValueError, "out of range"):
            read_rows(path)

    def tempdir(self):
        if not hasattr(self, "_tempdir"):
            self._tempdir = tempfile.TemporaryDirectory()
            self.addCleanup(self._tempdir.cleanup)
        return self._tempdir.name

class CourseCoverageTests(unittest.TestCase):
    def test_c1_c2_oov_report_is_only_dictionary_coverage(self):
        data = {"items": [
            {"cefr": "C1", "prompt_en": "The deliberate extrapolation is controversial."},
            {"cefr": "C2", "prompt_en": "Methodological uncertainty is inevitable."}
        ]}
        prompts = collect_prompts(data)
        result = coverage({"the", "deliberate", "is", "inevitable"},
                          prompts)
        self.assertEqual(result["status"], "lexicon_coverage_not_pronunciation_accuracy")
        self.assertIn("extrapolation", result["levels"]["C1"]["top_OOV"])
        self.assertIn("methodological", result["levels"]["C2"]["top_OOV"])


if __name__ == "__main__":
    unittest.main()
