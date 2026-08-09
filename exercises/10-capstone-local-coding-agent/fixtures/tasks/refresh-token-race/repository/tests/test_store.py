import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.store import RefreshTokenStore


class StoreTest(unittest.TestCase):
    def test_only_one_concurrent_consumer_succeeds(self) -> None:
        store = RefreshTokenStore()
        barrier = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _index: store.consume("token-1", before_commit=barrier.wait), range(2)))
        self.assertEqual(sorted(results), [False, True])


if __name__ == "__main__":
    unittest.main()
