"""빈 패턴을 일치하지 않는 것으로 처리한 결함."""

from _load_reference import *  # noqa: F401,F403


def kmp_find(text, pattern):
    if pattern == "":
        return -1
    return reference.kmp_find(text, pattern)
