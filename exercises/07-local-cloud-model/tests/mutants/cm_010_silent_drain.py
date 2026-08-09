from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def drain_events(self, max_attempts: int = 2, max_steps: int = 100) -> None:
        if max_attempts <= 0 or max_steps <= 0:
            raise ValueError("limits must be positive")
        steps = 0
        while self.queue and steps < max_steps:
            self.process_next(max_attempts=max_attempts)
            steps += 1
