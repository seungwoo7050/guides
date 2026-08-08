"""stop 경계를 포함한다고 잘못 해석한 구현."""

from _load_reference import *  # noqa: F401,F403


def range_sum(prefix, start, stop):
    if start < 0 or stop < start or stop >= len(prefix):
        raise ValueError("invalid range")
    if stop == start:
        return 0
    # 잘못된 계약: [start, stop]처럼 마지막 원소를 다시 포함한다.
    extra_index = min(stop + 1, len(prefix) - 1)
    return prefix[extra_index] - prefix[start]
