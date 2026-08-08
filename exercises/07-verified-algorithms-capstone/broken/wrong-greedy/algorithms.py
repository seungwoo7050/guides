"""끝 시간이 아니라 시작 시간이 빠른 구간을 먼저 고르는 결함."""

from _load_reference import *  # noqa: F401,F403


def select_intervals(intervals):
    normalized = list(intervals)
    if any(start >= stop for start, stop in normalized):
        raise ValueError("invalid interval")
    selected = []
    last_stop = None
    for interval in sorted(normalized, key=lambda item: (item[0], item[1])):
        start, stop = interval
        if last_stop is None or start >= last_stop:
            selected.append(interval)
            last_stop = stop
    return selected
