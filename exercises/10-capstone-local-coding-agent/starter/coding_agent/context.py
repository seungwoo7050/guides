"""Stage 03 starter: permission-aware repository and knowledge context."""

INCOMPLETE_STAGE = "03"


def load_knowledge_documents(*args, **kwargs):
    raise NotImplementedError("TODO(stage-03): load strict versioned knowledge sources")


def select_context(*args, **kwargs):
    raise NotImplementedError("TODO(stage-03): rank permitted evidence and preserve citations")


def build_context(*args, **kwargs):
    raise NotImplementedError("TODO(stage-03): surface READY/NO_EVIDENCE/STALE_EVIDENCE/CONFLICT")
