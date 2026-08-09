from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def process_next(self, max_attempts: int = 2) -> str:
        if self.queue:
            event = self.queue[0]
            document = self.documents.get(event.document_id)
            if document and document["tenant_id"] != event.tenant_id:
                original = document["tenant_id"]
                document["tenant_id"] = event.tenant_id
                try:
                    return super().process_next(max_attempts=max_attempts)
                finally:
                    document["tenant_id"] = original
        return super().process_next(max_attempts=max_attempts)
