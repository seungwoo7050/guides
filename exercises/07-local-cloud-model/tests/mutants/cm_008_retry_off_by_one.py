from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def process_next(self, max_attempts: int = 2) -> str:
        return super().process_next(max_attempts=max_attempts + 1)
