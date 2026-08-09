from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def process_next(self, max_attempts: int = 2) -> str:
        if self.queue:
            event = self.queue[0]
            identity = (event.tenant_id, event.event_id)
            if identity in self.processed_events:
                self.queue.pop(0)
                sequence = self.usage_for(event.tenant_id)
                output_id = f"duplicate:{event.tenant_id}:{event.document_id}:{sequence}"
                self.outputs[output_id] = {
                    "tenant_id": event.tenant_id,
                    "document_id": event.document_id,
                    "source_event": event.event_id,
                }
                self.usage[event.tenant_id] = sequence + 1
                return "processed"
        return super().process_next(max_attempts=max_attempts)
