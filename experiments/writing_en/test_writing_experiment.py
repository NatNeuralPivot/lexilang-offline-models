#!/usr/bin/env python3
"""Offline synthetic unit tests; these fixtures are NOT model files."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_gec_candidate import assemble, sha256, check_metadata, REQUIRED, MODEL_ID
from verify_gec_candidate import verify
from evaluate_writing_smoke import evaluate


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = self.root / "source"
        self.files.mkdir()
        # Synthetic 20 MB file passes only SIZE gates; it is not a valid ONNX graph.
        with (self.files / "model.onnx").open("wb") as file:
            file.truncate(20_000_010)
            file.seek(20_000_009)
            file.write(b"f")
        (self.files / "tokenizer.json").write_text(
            '{"model":{"type":"BPE"},"padding":null}', encoding="utf-8")
        (self.files / "labels.json").write_text(
            '{"labels":["$KEEP","$DELETE","$APPEND_the"]}', encoding="utf-8")
        (self.files / "verb-form-vocab.txt").write_text(
            "am_is:are\nwent_go:go\n", encoding="utf-8")
        self.meta = {
            "revision": "a" * 40,
            "license": "apache-2.0",
            "source": MODEL_ID,
            "files": {name: {"bytes": sha256(self.files / name)[0],
                             "sha256": sha256(self.files / name)[1]}
                      for name in REQUIRED},
        }
        self.output = self.root / "candidate"

    def test_four_realistically_sized_synthetic_files_copy(self):
        record = assemble(self.files, self.output, self.meta)
        self.assertEqual(record["status"], "research_candidate_not_release_ready")
        self.assertEqual(verify(self.output)["files"], 4)
        self.assertFalse(record["gates"]["licensing_provenance_approved"])
        self.assertFalse(record["gates"]["macos_onnx_inference_passed"])

    def test_modified_candidate_digest_fails(self):
        assemble(self.files, self.output, self.meta)
        (self.output / "assets" / "labels.json").write_text('{"corrupted":true}', "utf-8")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verify(self.output)

    def test_incomplete_model_is_rejected(self):
        (self.files / "verb-form-vocab.txt").unlink()
        with self.assertRaises(FileNotFoundError):
            assemble(self.files, self.output, self.meta)

    def test_untrusted_license_is_rejected(self):
        self.meta["license"] = "cc-by-nc-sa-4.0"
        with self.assertRaisesRegex(ValueError, "Unreviewed"):
            assemble(self.files, self.output, self.meta)

    def test_unpinned_version_is_rejected(self):
        self.meta["revision"] = "main"
        with self.assertRaisesRegex(ValueError, "revision"):
            assemble(self.files, self.output, self.meta)

    def test_unknown_extra_model_file_rejected(self):
        self.meta["files"]["other.bin"] = {"bytes": 10, "sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "Missing or unexpected"):
            assemble(self.files, self.output, self.meta)

    def test_upstream_digest_mismatch_rejected(self):
        self.meta["files"]["model.onnx"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            assemble(self.files, self.output, self.meta)

    def test_candidate_is_immutable(self):
        assemble(self.files, self.output, self.meta)
        with self.assertRaises(FileExistsError):
            assemble(self.files, self.output, self.meta)


class SmokeTests(unittest.TestCase):
    def cases(self):
        return [
            {"id":"A1","type":"error","text":"She go to school."},
            {"id":"C2","type":"keep","text":"Had she known, she would have responded."},
        ]

    def test_changes_known_error_and_preserves_valid_syntax(self):
        predictions = [
            {"id":"A1","original":"She go to school.","revised_text":"She goes to school."},
            {"id":"C2","original":"Had she known, she would have responded.",
             "revised_text":"Had she known, she would have responded."},
        ]
        report = evaluate(self.cases(), predictions)
        self.assertEqual(report["errors_causing_a_change"], 1)
        self.assertEqual(report["valid_inputs_preserved"], 1)
        self.assertFalse(report["failures"])

    def test_missing_output_rejected(self):
        predictions = [
            {"id":"A1","original":"She go to school.","revised_text":"She goes to school."}
        ]
        with self.assertRaisesRegex(ValueError, "Missing or extra"):
            evaluate(self.cases(), predictions)

    def test_source_mutation_rejected(self):
        predictions = [
            {"id":"A1","original":"other","revised_text":"She goes to school."},
            {"id":"C2","original":"Had she known, she would have responded.",
             "revised_text":"Had she known, she would have responded."},
        ]
        with self.assertRaisesRegex(ValueError, "Source text differs"):
            evaluate(self.cases(), predictions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
