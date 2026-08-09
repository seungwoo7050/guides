from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def read_document(self, requester_tenant: str, document_id: str) -> str:
        self._require_active(requester_tenant)
        document = self.documents.get(document_id)
        if not document:
            raise AccessDenied(document_id)
        return str(document["content"])
