import unittest

from app.cli import run


class CliTest(unittest.TestCase):
    def test_normal_apply(self) -> None:
        store: dict[str, str] = {}
        self.assertEqual(run(["color", "blue"], store), "applied color=blue")
        self.assertEqual(store, {"color": "blue"})


if __name__ == "__main__":
    unittest.main()
