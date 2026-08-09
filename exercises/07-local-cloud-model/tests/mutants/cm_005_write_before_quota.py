from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def store_document(self, tenant_id: str, document_id: str, content: str) -> None:
        tenant = self._require_active(tenant_id)
        existing = self.documents.get(document_id)
        if existing and existing["tenant_id"] != tenant_id:
            raise AccessDenied(document_id)
        self.documents[document_id] = {"tenant_id": tenant_id, "content": content}
        active_count = sum(
            1 for document in self.documents.values() if document["tenant_id"] == tenant_id
        )
        if active_count > self.PLAN_LIMITS[tenant["plan"]]:
            raise QuotaExceeded(f"{tenant_id}: over active document capacity")
