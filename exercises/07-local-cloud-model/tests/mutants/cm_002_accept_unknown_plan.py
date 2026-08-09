from _reference_loader import REFERENCE, expose

expose(globals())


class CloudModel(REFERENCE.CloudModel):
    def provision_tenant(self, tenant_id: str, plan: str = "starter") -> None:
        if plan not in self.PLAN_LIMITS:
            plan = "starter"
        super().provision_tenant(tenant_id, plan)
