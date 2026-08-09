"""Stage 06 starter: edit-test-repair policy."""

INCOMPLETE_STAGE = "06"


def classify_failure(result):
    raise NotImplementedError("TODO(stage-06): distinguish task, policy, budget, and environment failures")


class IterationTracker:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("TODO(stage-06): stop repeated non-progressing repairs")
