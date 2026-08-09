from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def enqueue_event(self, event_id: str, tenant_id: str, document_id: str) -> None:
        self._require_active(tenant_id)
        self.event_registry.setdefault((tenant_id, event_id), document_id)
        self.queue.append(Event(event_id, tenant_id, document_id))
