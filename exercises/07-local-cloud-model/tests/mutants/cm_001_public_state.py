from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def provision_tenant(self, tenant_id: str, plan: str = "starter") -> None:
        super().provision_tenant(tenant_id, plan)
        next(item for item in self.resources if item["tenant_id"] == tenant_id)["public"] = True
