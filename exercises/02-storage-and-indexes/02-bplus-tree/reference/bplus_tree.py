from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from typing import Generic, TypeVar

V = TypeVar("V")


@dataclass
class Node(Generic[V]):
    leaf: bool
    keys: list[int] = field(default_factory=list)
    children: list["Node[V]"] = field(default_factory=list)
    values: list[V] = field(default_factory=list)
    next: "Node[V] | None" = None


class BPlusTree(Generic[V]):
    def __init__(self, order: int = 4) -> None:
        if order < 3:
            raise ValueError("order must be at least 3")
        self.order = order
        self.max_keys = order - 1
        self.root: Node[V] = Node(leaf=True)

    def _find_leaf(self, key: int) -> tuple[Node[V], list[Node[V]]]:
        node = self.root
        path: list[Node[V]] = []
        while not node.leaf:
            path.append(node)
            node = node.children[bisect_right(node.keys, key)]
        return node, path

    def insert(self, key: int, value: V) -> None:
        if not isinstance(key, int):
            raise TypeError("key must be int")
        leaf, path = self._find_leaf(key)
        index = bisect_left(leaf.keys, key)
        if index < len(leaf.keys) and leaf.keys[index] == key:
            leaf.values[index] = value
            return
        leaf.keys.insert(index, key)
        leaf.values.insert(index, value)
        if len(leaf.keys) > self.max_keys:
            self._split_leaf(leaf, path)

    def _split_leaf(self, leaf: Node[V], path: list[Node[V]]) -> None:
        split = (len(leaf.keys) + 1) // 2
        right = Node[V](leaf=True)
        right.keys = leaf.keys[split:]
        right.values = leaf.values[split:]
        leaf.keys = leaf.keys[:split]
        leaf.values = leaf.values[:split]
        right.next = leaf.next
        leaf.next = right
        self._insert_in_parent(leaf, right.keys[0], right, path)

    def _insert_in_parent(
        self,
        left: Node[V],
        separator: int,
        right: Node[V],
        path: list[Node[V]],
    ) -> None:
        if not path:
            self.root = Node(leaf=False, keys=[separator], children=[left, right])
            return
        parent = path.pop()
        child_index = parent.children.index(left)
        parent.keys.insert(child_index, separator)
        parent.children.insert(child_index + 1, right)
        if len(parent.keys) > self.max_keys:
            self._split_internal(parent, path)

    def _split_internal(self, node: Node[V], path: list[Node[V]]) -> None:
        middle = len(node.keys) // 2
        promote = node.keys[middle]
        right = Node[V](leaf=False)
        right.keys = node.keys[middle + 1 :]
        right.children = node.children[middle + 1 :]
        node.keys = node.keys[:middle]
        node.children = node.children[: middle + 1]
        self._insert_in_parent(node, promote, right, path)

    def get(self, key: int) -> V:
        leaf, _ = self._find_leaf(key)
        index = bisect_left(leaf.keys, key)
        if index == len(leaf.keys) or leaf.keys[index] != key:
            raise KeyError(key)
        return leaf.values[index]

    def range(self, start: int, end: int) -> list[tuple[int, V]]:
        if start > end:
            return []
        leaf, _ = self._find_leaf(start)
        result: list[tuple[int, V]] = []
        while leaf is not None:
            for key, value in zip(leaf.keys, leaf.values, strict=True):
                if key < start:
                    continue
                if key > end:
                    return result
                result.append((key, value))
            leaf = leaf.next
        return result

    def validate(self) -> None:
        leaf_depths: set[int] = set()
        leaves: list[Node[V]] = []

        def walk(node: Node[V], depth: int, low: int | None, high: int | None) -> tuple[int, int]:
            if node.keys != sorted(node.keys) or len(node.keys) > self.max_keys:
                raise AssertionError("invalid key ordering or node overflow")
            if node.leaf:
                if len(node.keys) != len(node.values) or node.children:
                    raise AssertionError("invalid leaf shape")
                if not node.keys and node is not self.root:
                    raise AssertionError("empty non-root leaf")
                for key in node.keys:
                    if low is not None and key < low:
                        raise AssertionError("leaf key below lower bound")
                    if high is not None and key >= high:
                        raise AssertionError("leaf key above upper bound")
                leaf_depths.add(depth)
                leaves.append(node)
                return (node.keys[0], node.keys[-1]) if node.keys else (0, 0)

            if node.values or len(node.children) != len(node.keys) + 1:
                raise AssertionError("invalid internal shape")
            ranges: list[tuple[int, int]] = []
            for index, child in enumerate(node.children):
                child_low = low if index == 0 else node.keys[index - 1]
                child_high = high if index == len(node.children) - 1 else node.keys[index]
                ranges.append(walk(child, depth + 1, child_low, child_high))
            for index, separator in enumerate(node.keys):
                if ranges[index + 1][0] != separator:
                    raise AssertionError("separator is not right subtree minimum")
            return ranges[0][0], ranges[-1][1]

        walk(self.root, 0, None, None)
        if len(leaf_depths) != 1:
            raise AssertionError("leaves are not at the same depth")
        for index, leaf in enumerate(leaves):
            expected = leaves[index + 1] if index + 1 < len(leaves) else None
            if leaf.next is not expected:
                raise AssertionError("broken leaf chain")
