from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import unittest
from pathlib import Path

from contract import CHECKS, run_contract


BASE = Path(__file__).resolve().parents[1]
profile = os.environ.get("CLOUD_MODEL_PROFILE", "reference")
IMPLEMENTATION = Path(
    os.environ.get(
        "CLOUD_MODEL_IMPLEMENTATION",
        str(BASE / profile / "cloud_model.py"),
    )
).resolve()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("cloud_model_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        spec.loader.exec_module(module)
    return module


MODULE = load_module(IMPLEMENTATION)
RESULTS = {record["id"]: record for record in run_contract(MODULE)}


class CloudModelContractTest(unittest.TestCase):
    maxDiff = None


def add_test(check_id: str, title: str) -> None:
    def test(self: CloudModelContractTest) -> None:
        record = RESULTS[check_id]
        self.assertEqual(
            "pass",
            record["status"],
            f"{check_id} {title}: {record['message']}",
        )

    slug = title.lower().replace(" ", "_").replace("-", "_")
    setattr(CloudModelContractTest, f"test_{check_id.lower().replace('-', '_')}_{slug}", test)


for specification in CHECKS:
    add_test(specification.id, specification.title)


if __name__ == "__main__":
    unittest.main()
