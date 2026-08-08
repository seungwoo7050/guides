from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/analyze_tcpdump.py"
spec = importlib.util.spec_from_file_location("analyze_tcpdump", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class TcpdumpAnalyzerTests(unittest.TestCase):
    def test_complete_handshake_is_detected(self) -> None:
        result = module.analyze((ROOT / "fixtures/handshake.txt").read_text(encoding="utf-8"))
        self.assertTrue(result["handshake_complete"])
        self.assertEqual(result["packet_count"], 5)
        self.assertEqual(result["retransmission_candidates"], [])

    def test_wrong_handshake_ack_is_rejected(self) -> None:
        trace = (ROOT / "fixtures/handshake.txt").read_text(encoding="utf-8")
        trace = trace.replace("ack 1001", "ack 1002", 1)
        self.assertFalse(module.analyze(trace)["handshake_complete"])

    def test_repeated_syn_is_reported_as_candidate(self) -> None:
        result = module.analyze(
            (ROOT / "fixtures/retransmission.txt").read_text(encoding="utf-8")
        )
        self.assertTrue(result["handshake_complete"])
        candidates = result["retransmission_candidates"]
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["flags"], "S")
        self.assertGreater(candidates[0]["delay_seconds"], 1.0)

    def test_unrelated_lines_are_ignored(self) -> None:
        self.assertEqual(module.parse_trace("tcpdump: listening on lo\nnoise\n"), [])


if __name__ == "__main__":
    unittest.main()
