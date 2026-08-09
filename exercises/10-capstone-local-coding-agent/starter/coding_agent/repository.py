"""Stage 02 starter: immutable Git snapshot, discovery, and cited search."""

INCOMPLETE_STAGE = "02"


class RepositoryReader:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("TODO(stage-02): bind reads to a repository snapshot")


def snapshot_repository(*args, **kwargs):
    raise NotImplementedError("TODO(stage-02): capture Git, index, worktree, and file identity")


def discover_repository(*args, **kwargs):
    raise NotImplementedError("TODO(stage-02): discover instructions, manifests, and check commands")


def search_repository(*args, **kwargs):
    raise NotImplementedError("TODO(stage-02): implement bounded snapshot-aware search")
