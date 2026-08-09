import unittest

from app.tokens import is_token_valid


class TokenTest(unittest.TestCase):
    def test_future_token_is_valid(self) -> None:
        self.assertTrue(is_token_valid(expires_at=11, now=10))

    def test_past_token_is_expired(self) -> None:
        self.assertFalse(is_token_valid(expires_at=9, now=10))

    def test_equal_expiry_is_expired(self) -> None:
        self.assertFalse(is_token_valid(expires_at=10, now=10))


if __name__ == "__main__":
    unittest.main()
