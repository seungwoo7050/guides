from typing import Any

from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def evidence_snapshot(self, tenant_id: str) -> dict[str, Any]:
        value = super().evidence_snapshot(tenant_id)
        value["document_contents"] = sorted(
            document["content"]
            for document in self.documents.values()
            if document["tenant_id"] == tenant_id
        )
        return value
