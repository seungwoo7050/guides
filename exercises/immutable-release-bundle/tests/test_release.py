from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from validate_release import validate_bundle

ROOT = Path(__file__).resolve().parents[1]


# [Implementation 8] Validation regression suite
class ReleaseBundleTest(unittest.TestCase):
    def copy_bundle(self) -> Path:
        temporary = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temporary, ignore_errors=True)
        for name in ("Dockerfile", "app.py", "release.yaml"):
            shutil.copy2(ROOT / name, temporary / name)
        return temporary

    def test_bundle_and_payload_are_deterministic(self) -> None:
        self.assertEqual(validate_bundle(ROOT), [])
        output = subprocess.check_output(["python", str(ROOT / "app.py")], text=True)
        self.assertEqual(output, '{"status":"ready"}\n')

    def test_sbom_subject_mismatch_is_rejected(self) -> None:
        bundle = self.copy_bundle()
        manifest = yaml.safe_load((bundle / "release.yaml").read_text(encoding="utf-8"))
        manifest["supply_chain"]["sbom"]["subject_digest"] = "sha256:" + "f" * 64
        (bundle / "release.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        errors = validate_bundle(bundle)
        self.assertTrue(any("SBOM subject digest" in error for error in errors))

    def test_mutable_base_and_root_runtime_are_rejected(self) -> None:
        bundle = self.copy_bundle()
        dockerfile = (bundle / "Dockerfile").read_text(encoding="utf-8")
        dockerfile = dockerfile.replace("python:3.14.0-alpine3.22", "python:latest").replace("USER app", "USER root")
        (bundle / "Dockerfile").write_text(dockerfile, encoding="utf-8")
        errors = validate_bundle(bundle)
        self.assertTrue(any("non-latest version" in error for error in errors))
        self.assertTrue(any("non-root runtime user" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
