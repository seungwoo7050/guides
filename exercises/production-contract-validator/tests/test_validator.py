from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from production_contract_validator.cli import main
from production_contract_validator.validator import validate_contract

ROOT = Path(__file__).resolve().parents[1]


# [Implementation 8] Validation regression suite
class ContractValidatorTest(unittest.TestCase):
    def load_example(self) -> dict:
        return yaml.safe_load((ROOT / "examples/notes-service.yaml").read_text(encoding="utf-8"))

    def write_contract(self, value: dict) -> Path:
        temporary = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
        with temporary:
            yaml.safe_dump(value, temporary, sort_keys=False)
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_example_is_valid(self) -> None:
        path = ROOT / "examples/notes-service.yaml"
        self.assertEqual(validate_contract(path), [])
        self.assertEqual(main([str(path)]), 0)

    def test_public_database_and_local_backup_are_rejected(self) -> None:
        value = self.load_example()
        value["endpoints"]["public"].append(
            {"name": "database", "port": 3306, "protocol": "mysql", "owner": "data-owner"}
        )
        value["data"][0]["external_recovery_copy"] = False
        errors = validate_contract(self.write_contract(value))
        self.assertTrue(any("unexpected public service port: 3306" in error for error in errors))
        self.assertTrue(any("external recovery copy" in error for error in errors))

    def test_health_only_measurement_and_missing_rollback_test_are_rejected(self) -> None:
        value = copy.deepcopy(self.load_example())
        value["objectives"]["availability"]["path"] = "/healthz"
        value["readiness"]["rollback_tested"] = False
        errors = validate_contract(self.write_contract(value))
        self.assertTrue(any("user-facing capability" in error for error in errors))
        self.assertTrue(any("rollback_tested" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
