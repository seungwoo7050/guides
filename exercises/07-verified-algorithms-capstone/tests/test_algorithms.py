from __future__ import annotations

from itertools import combinations, product
import importlib.util
import os
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION = os.environ.get("EXERCISE_IMPL_PATH", "reference")
IMPLEMENTATION_PATH = (ROOT / IMPLEMENTATION / "algorithms.py").resolve()
if ROOT not in IMPLEMENTATION_PATH.parents:
    raise RuntimeError("implementation path가 exercise 밖을 가리킵니다.")
if not IMPLEMENTATION_PATH.is_file():
    raise RuntimeError(f"implementation file이 없습니다: {IMPLEMENTATION_PATH}")

spec = importlib.util.spec_from_file_location("exercise_subject", IMPLEMENTATION_PATH)
assert spec is not None and spec.loader is not None
sys.path.insert(0, str(IMPLEMENTATION_PATH.parent))
subject = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = subject
spec.loader.exec_module(subject)


def all_pairs_distances(
    size: int,
    edges: list[tuple[int, int, int]],
) -> list[list[int | None]]:
    distance: list[list[int | None]] = [[None] * size for _ in range(size)]
    for vertex in range(size):
        distance[vertex][vertex] = 0
    for source, target, weight in edges:
        current = distance[source][target]
        if current is None or weight < current:
            distance[source][target] = weight
    for middle in range(size):
        for source in range(size):
            if distance[source][middle] is None:
                continue
            for target in range(size):
                if distance[middle][target] is None:
                    continue
                candidate = distance[source][middle] + distance[middle][target]
                current = distance[source][target]
                if current is None or candidate < current:
                    distance[source][target] = candidate
    return distance


def brute_interval_count(intervals: list[tuple[int, int]]) -> int:
    best = 0
    for count in range(len(intervals) + 1):
        for subset in combinations(intervals, count):
            ordered = sorted(subset)
            if all(left[1] <= right[0] for left, right in zip(ordered, ordered[1:])):
                best = max(best, count)
    return best


def brute_knapsack(items: list[tuple[int, int]], capacity: int) -> int:
    best = 0
    for count in range(len(items) + 1):
        for selected in combinations(range(len(items)), count):
            weight = sum(items[index][0] for index in selected)
            if weight <= capacity:
                best = max(best, sum(items[index][1] for index in selected))
    return best


def valid_red_black_tree(root: object) -> tuple[bool, int | None]:
    if root is not None and root.color != "black":
        return False, None

    def visit(node: object, lower: int | None, upper: int | None) -> int | None:
        if node is None:
            return 1
        if node.color not in {"red", "black"}:
            return None
        if lower is not None and node.key <= lower:
            return None
        if upper is not None and node.key >= upper:
            return None
        if node.color == "red" and (
            (node.left is not None and node.left.color == "red")
            or (node.right is not None and node.right.color == "red")
        ):
            return None
        left = visit(node.left, lower, node.key)
        right = visit(node.right, node.key, upper)
        if left is None or right is None or left != right:
            return None
        return left + (1 if node.color == "black" else 0)

    height = visit(root, None, None)
    return height is not None, height


def complete_tree(colors: tuple[str, ...]) -> object:
    nodes = {
        key: subject.RedBlackNode(key, color)
        for key, color in zip((4, 2, 6, 1, 3, 5, 7), colors)
    }
    nodes[4].left, nodes[4].right = nodes[2], nodes[6]
    nodes[2].left, nodes[2].right = nodes[1], nodes[3]
    nodes[6].left, nodes[6].right = nodes[5], nodes[7]
    return nodes[4]


def brute_mst_weight(
    vertex_count: int,
    edges: list[tuple[int, int, int]],
) -> int:
    if vertex_count == 0:
        return 0
    best: int | None = None
    for chosen in combinations(edges, vertex_count - 1):
        groups = list(range(vertex_count))

        def find(vertex: int) -> int:
            while groups[vertex] != vertex:
                vertex = groups[vertex]
            return vertex

        acyclic = True
        for source, target, _weight in chosen:
            left, right = find(source), find(target)
            if left == right:
                acyclic = False
                break
            groups[right] = left
        if acyclic and len({find(vertex) for vertex in range(vertex_count)}) == 1:
            weight = sum(edge[2] for edge in chosen)
            best = weight if best is None else min(best, weight)
    if best is None:
        raise ValueError("연결된 spanning tree가 없습니다.")
    return best


def brute_min_cut(capacity: list[list[int]], source: int, sink: int) -> int:
    vertices = [vertex for vertex in range(len(capacity)) if vertex not in {source, sink}]
    best: int | None = None
    for mask in range(1 << len(vertices)):
        source_side = {source}
        source_side.update(
            vertex for index, vertex in enumerate(vertices) if mask & (1 << index)
        )
        cut = sum(
            capacity[left][right]
            for left in source_side
            for right in range(len(capacity))
            if right not in source_side
        )
        best = cut if best is None else min(best, cut)
    assert best is not None
    return best


def brute_lcs_length(left: str, right: str) -> int:
    def is_subsequence(candidate: str, text: str) -> bool:
        position = 0
        for character in text:
            if position < len(candidate) and candidate[position] == character:
                position += 1
        return position == len(candidate)

    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    best = 0
    for mask in range(1 << len(shorter)):
        candidate = "".join(
            character
            for index, character in enumerate(shorter)
            if mask & (1 << index)
        )
        if len(candidate) > best and is_subsequence(candidate, longer):
            best = len(candidate)
    return best


class DataStructureTests(unittest.TestCase):
    def test_prefix_contract_and_random_ranges(self) -> None:
        self.assertEqual(subject.prefix_sums([]), [0])
        self.assertEqual(subject.prefix_sums([3, -2, 5]), [0, 3, 1, 6])

        source = random.Random(20241214)
        values = [source.randrange(-20, 21) for _ in range(80)]
        prefix = subject.prefix_sums(values)
        self.assertEqual(len(prefix), len(values) + 1)
        for _ in range(250):
            start = source.randrange(len(values) + 1)
            stop = source.randrange(start, len(values) + 1)
            self.assertEqual(subject.range_sum(prefix, start, stop), sum(values[start:stop]))

    def test_range_sum_rejects_invalid_half_open_ranges(self) -> None:
        prefix = subject.prefix_sums([1, 2, 3])
        for start, stop in [(-1, 1), (2, 1), (0, 4), (4, 4)]:
            with self.subTest(start=start, stop=stop):
                with self.assertRaises(ValueError):
                    subject.range_sum(prefix, start, stop)

    def test_lower_bound_matches_bisect_with_duplicates(self) -> None:
        from bisect import bisect_left

        cases = [
            [],
            [1],
            [1, 1, 1],
            [-3, -1, 0, 0, 4, 9],
        ]
        source = random.Random(20250102)
        cases.append(sorted(source.randrange(-30, 31) for _ in range(120)))
        for values in cases:
            for target in range(-35, 36):
                self.assertEqual(subject.lower_bound(values, target), bisect_left(values, target))

    def test_red_black_all_complete_tree_colorings(self) -> None:
        self.assertEqual(subject.red_black_height(None), 1)
        for colors in product(("red", "black"), repeat=7):
            tree = complete_tree(colors)
            expected_valid, expected_height = valid_red_black_tree(tree)
            if expected_valid:
                self.assertEqual(subject.red_black_height(tree), expected_height)
            else:
                with self.assertRaises(ValueError):
                    subject.red_black_height(tree)

    def test_red_black_rejects_bst_and_color_errors(self) -> None:
        invalid_color = subject.RedBlackNode(2, "blue")
        with self.assertRaises(ValueError):
            subject.red_black_height(invalid_color)

        bad_order = subject.RedBlackNode(
            4,
            "black",
            left=subject.RedBlackNode(5, "black"),
            right=subject.RedBlackNode(6, "black"),
        )
        with self.assertRaises(ValueError):
            subject.red_black_height(bad_order)


class DesignTechniqueTests(unittest.TestCase):
    def test_knapsack_matches_subset_enumeration(self) -> None:
        source = random.Random(20250130)
        self.assertEqual(subject.knapsack_01([], 0), 0)
        for _ in range(70):
            items = [(source.randrange(1, 8), source.randrange(-3, 16)) for _ in range(8)]
            capacity = source.randrange(0, 20)
            self.assertEqual(subject.knapsack_01(items, capacity), brute_knapsack(items, capacity))

    def test_knapsack_rejects_invalid_contract(self) -> None:
        with self.assertRaises(ValueError):
            subject.knapsack_01([], -1)
        with self.assertRaises(ValueError):
            subject.knapsack_01([(0, 5)], 10)
        with self.assertRaises(ValueError):
            subject.knapsack_01([(-2, 5)], 10)

    def test_interval_selection_matches_exhaustive_optimum(self) -> None:
        source = random.Random(20250201)
        specific = [(0, 100), (1, 2), (2, 3), (3, 4)]
        self.assertEqual(len(subject.select_intervals(specific)), 3)
        for _ in range(80):
            intervals: list[tuple[int, int]] = []
            for _ in range(8):
                start = source.randrange(0, 12)
                intervals.append((start, start + source.randrange(1, 5)))
            selected = subject.select_intervals(intervals)
            self.assertEqual(len(selected), brute_interval_count(intervals))
            self.assertTrue(all(left[1] <= right[0] for left, right in zip(selected, selected[1:])))

    def test_interval_selection_rejects_empty_or_reversed_ranges(self) -> None:
        for intervals in [[(1, 1)], [(3, 2)], [(0, 1), (5, 4)]]:
            with self.assertRaises(ValueError):
                subject.select_intervals(intervals)

    def test_lcs_matches_subsequence_enumeration(self) -> None:
        source = random.Random(20250205)
        self.assertEqual(subject.lcs_length("", ""), 0)
        self.assertEqual(subject.lcs_length("abc", "abc"), 3)
        self.assertEqual(subject.lcs_length("abc", "def"), 0)
        for _ in range(100):
            left = "".join(source.choice("abcd") for _ in range(source.randrange(9)))
            right = "".join(source.choice("abcd") for _ in range(source.randrange(9)))
            self.assertEqual(subject.lcs_length(left, right), brute_lcs_length(left, right))


class GraphTests(unittest.TestCase):
    def test_bfs_distances_against_unit_weight_floyd_warshall(self) -> None:
        source = random.Random(20250111)
        self.assertEqual(subject.bfs_distances([[]], 0), [0])
        for _ in range(50):
            size = 7
            graph = [
                [
                    target
                    for target in range(size)
                    if target != vertex and source.random() < 0.25
                ]
                for vertex in range(size)
            ]
            edges = [
                (vertex, target, 1)
                for vertex, neighbors in enumerate(graph)
                for target in neighbors
            ]
            expected = all_pairs_distances(size, edges)[0]
            self.assertEqual(subject.bfs_distances(graph, 0), expected)

    def test_bfs_rejects_invalid_vertices(self) -> None:
        with self.assertRaises(ValueError):
            subject.bfs_distances([], 0)
        with self.assertRaises(ValueError):
            subject.bfs_distances([[1], [2]], 0)

    def test_dijkstra_matches_independent_all_pairs(self) -> None:
        source = random.Random(20250118)
        for _ in range(45):
            size = 8
            edges = [
                (left, right, source.randrange(0, 10))
                for left in range(size)
                for right in range(size)
                if left != right and source.random() < 0.2
            ]
            self.assertEqual(subject.dijkstra(size, iter(edges), 0), all_pairs_distances(size, edges)[0])

    def test_dijkstra_rejects_negative_edges_and_bad_vertices(self) -> None:
        with self.assertRaises(ValueError):
            subject.dijkstra(2, [(0, 1, -1)], 0)
        with self.assertRaises(ValueError):
            subject.dijkstra(2, [(0, 2, 1)], 0)

    def test_bellman_ford_handles_negative_edges_and_cycle_contract(self) -> None:
        source = random.Random(20250125)
        for _ in range(50):
            size = 7
            # DAG이므로 음수 edge는 있어도 cycle은 없다.
            edges = [
                (left, right, source.randrange(-5, 10))
                for left in range(size)
                for right in range(left + 1, size)
                if source.random() < 0.35
            ]
            self.assertEqual(subject.bellman_ford(size, edges, 0), all_pairs_distances(size, edges)[0])

        with self.assertRaises(ValueError):
            subject.bellman_ford(3, [(0, 1, 1), (1, 2, -2), (2, 1, -2)], 0)

        # 시작점에서 도달 불가능한 음수 cycle은 결과를 무효화하지 않는다.
        self.assertEqual(
            subject.bellman_ford(4, [(0, 1, 3), (2, 3, -2), (3, 2, -2)], 0),
            [0, 3, None, None],
        )

    def test_kruskal_matches_spanning_tree_enumeration(self) -> None:
        self.assertEqual(subject.kruskal_mst(0, []), (0, []))
        source = random.Random(20250215)
        for _ in range(40):
            size = 5
            edges = [(vertex - 1, vertex, source.randrange(1, 15)) for vertex in range(1, size)]
            edges.extend(
                (left, right, source.randrange(1, 15))
                for left in range(size)
                for right in range(left + 1, size)
                if (left, right) not in {(edge[0], edge[1]) for edge in edges}
                and source.random() < 0.35
            )
            weight, chosen = subject.kruskal_mst(size, iter(edges))
            self.assertEqual(weight, brute_mst_weight(size, edges))
            self.assertEqual(len(chosen), size - 1)

    def test_kruskal_rejects_disconnected_graph(self) -> None:
        with self.assertRaises(ValueError):
            subject.kruskal_mst(4, [(0, 1, 1), (2, 3, 1)])

    def test_max_flow_matches_all_cuts(self) -> None:
        source = random.Random(20250222)
        for _ in range(50):
            size = 6
            capacity = [
                [
                    source.randrange(1, 9)
                    if left != right and source.random() < 0.3
                    else 0
                    for right in range(size)
                ]
                for left in range(size)
            ]
            self.assertEqual(subject.max_flow(capacity, 0, size - 1), brute_min_cut(capacity, 0, size - 1))

    def test_max_flow_contract_errors(self) -> None:
        with self.assertRaises(ValueError):
            subject.max_flow([[0, 1], [0]], 0, 1)
        with self.assertRaises(ValueError):
            subject.max_flow([[0, -1], [0, 0]], 0, 1)
        self.assertEqual(subject.max_flow([[0]], 0, 0), 0)


class StringTests(unittest.TestCase):
    def test_kmp_matches_builtin_find(self) -> None:
        cases = [
            ("", ""),
            ("", "a"),
            ("aaaa", "aa"),
            ("abababac", "ababac"),
            ("abc", "abcd"),
            ("needle in a haystack", "hay"),
        ]
        for text, pattern in cases:
            self.assertEqual(subject.kmp_find(text, pattern), text.find(pattern))

        source = random.Random(20250208)
        alphabet = "abca"
        for _ in range(400):
            text = "".join(source.choice(alphabet) for _ in range(source.randrange(30)))
            pattern = "".join(source.choice(alphabet) for _ in range(source.randrange(10)))
            self.assertEqual(subject.kmp_find(text, pattern), text.find(pattern))


if __name__ == "__main__":
    unittest.main()
