from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def provision_tenant(self, tenant_id: str, plan: str = "starter") -> None:
        existing = self.tenants.get(tenant_id)
        if existing and existing["state"] == "DELETED":
            del self.tenants[tenant_id]
        super().provision_tenant(tenant_id, plan)
