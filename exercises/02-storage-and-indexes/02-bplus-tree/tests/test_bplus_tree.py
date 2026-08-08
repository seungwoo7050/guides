from __future__ import annotations

import random
import unittest

from bplus_tree import BPlusTree


class BPlusTreeTests(unittest.TestCase):
    def test_insert_search_and_root_growth(self) -> None:
        tree: BPlusTree[str] = BPlusTree(order=4)
        keys = list(range(100))
        random.Random(42).shuffle(keys)
        for key in keys:
            tree.insert(key, f"value-{key}")
            tree.validate()
        for key in range(100):
            self.assertEqual(tree.get(key), f"value-{key}")
        with self.assertRaises(KeyError):
            tree.get(1000)

    def test_duplicate_key_replaces_value(self) -> None:
        tree: BPlusTree[str] = BPlusTree(order=3)
        tree.insert(7, "old")
        tree.insert(7, "new")
        tree.validate()
        self.assertEqual(tree.get(7), "new")
        self.assertEqual(tree.range(0, 10), [(7, "new")])

    def test_range_crosses_leaf_boundaries(self) -> None:
        tree: BPlusTree[int] = BPlusTree(order=4)
        for key in range(0, 50, 2):
            tree.insert(key, key * 10)
        tree.validate()
        self.assertEqual(tree.range(9, 21), [(10, 100), (12, 120), (14, 140), (16, 160), (18, 180), (20, 200)])
        self.assertEqual(tree.range(30, 20), [])

    def test_rejects_non_integer_key(self) -> None:
        tree: BPlusTree[str] = BPlusTree()
        with self.assertRaises(TypeError):
            tree.insert("1", "bad")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
