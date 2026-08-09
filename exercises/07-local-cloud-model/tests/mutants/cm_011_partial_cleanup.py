from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def delete_tenant(self, tenant_id: str) -> None:
        tenant = self.tenants.get(tenant_id)
        if not tenant or tenant["state"] == "DELETED":
            return
        tenant["state"] = "DELETED"
        self.documents = {
            key: value
            for key, value in self.documents.items()
            if value["tenant_id"] != tenant_id
        }
