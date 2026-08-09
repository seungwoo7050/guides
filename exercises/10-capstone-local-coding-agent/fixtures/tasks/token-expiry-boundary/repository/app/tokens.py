def is_token_valid(*, expires_at: int, now: int) -> bool:
    """Return whether a token may still be used."""
    return expires_at >= now
