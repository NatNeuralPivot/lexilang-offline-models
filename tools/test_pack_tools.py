#!/usr/bin/env python3
"""Offline unit tests: all assets below are synthetic and NOT distributable models."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_pack import prepare
from verify_pack import verify


class PackToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = self.root / "source"
        self.assets.mkdir()
        (self.assets / "synthetic.bin").write_bytes(b"test-only fake model bytes")
        (self.assets / "LICENSES.txt").write_text(
            "Synthetic test only. No trained model weights are included.\n", encoding="utf-8"
        )
        self.meta = {
            "redistributionApproved": True,
            "reviewed": True,
            "reviewedBy": "unittest",
            "sourceURL": "https://example.org/only-for-tests",
            "reviewEvidence": "https://example.org/test-license",
            "license": "CC0-1.0",
        }
        self.spec = {
            "id": "fake-test-pack",
            "version": "0.0.1",
            "releaseTag": "fake-test-v0.0.1",
            "license": "CC0-1.0; synthetic test only",
            "notice": "Only fixture data, never publish this test as a model.",
            "assets": [
                {"name": "synthetic.bin", **self.meta},
                {"name": "LICENSES.txt", **self.meta},
            ]
        }

    def stage(self):
        return prepare(self.spec, self.assets, self.root / "dist")

    def test_roundtrip_integrity(self):
        folder = self.stage()
        self.assertEqual(verify(folder / "pack.json", folder), 4)
        data = json.loads((folder / "pack.json").read_text())
        self.assertEqual(data["id"], self.spec["id"])
        self.assertEqual([a["name"] for a in data["assets"]],
                         sorted(["synthetic.bin", "LICENSES.txt", "NOTICE.txt", "PROVENANCE.json"]))
        self.assertTrue(all(a["downloadURL"].startswith(
            "https://github.com/NatNeuralPivot/lexilang-offline-models/releases/download/"
        ) for a in data["assets"]))

    def test_modified_asset_fails_integrity(self):
        folder = self.stage()
        (folder / "synthetic.bin").write_bytes(b"tampered payload")
        with self.assertRaisesRegex(ValueError, "(mismatch|Invalid)"):
            verify(folder / "pack.json", folder)

    def test_unreviewed_asset_rejected(self):
        self.spec["assets"][0]["reviewed"] = False
        with self.assertRaisesRegex(ValueError, "Legal review"):
            self.stage()

    def test_redistribution_denied(self):
        self.spec["assets"][0]["redistributionApproved"] = False
        with self.assertRaisesRegex(ValueError, "Legal review"):
            self.stage()

    def test_missing_licenses_rejected(self):
        self.spec["assets"] = self.spec["assets"][:1]
        with self.assertRaisesRegex(ValueError, "LICENSES"):
            self.stage()

    def test_unsafe_filename_rejected(self):
        self.spec["assets"][0]["name"] = "../attack.bin"
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.stage()

    def test_duplicate_asset_rejected(self):
        self.spec["assets"].append(copy.deepcopy(self.spec["assets"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.stage()

    def test_rewrite_same_version_rejected(self):
        self.stage()
        with self.assertRaises(FileExistsError):
            self.stage()

    def test_wrong_host_in_manifest_rejected(self):
        folder = self.stage()
        data = json.loads((folder / "pack.json").read_text())
        data["assets"][0]["downloadURL"] = "https://bad.example/model.bin"
        (folder / "pack.json").write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Wrong release URL"):
            verify(folder / "pack.json", folder)


if __name__ == "__main__":
    unittest.main(verbosity=2)
