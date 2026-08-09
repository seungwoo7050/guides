"""Stage 08 starter: integrity-checked checkpoints and effect ledger."""

INCOMPLETE_STAGE = "08"


class CheckpointStore:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("TODO(stage-08): implement checkpoint integrity and resume")


class OperationLedger:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("TODO(stage-08): implement STARTED/COMPLETED reconciliation")
