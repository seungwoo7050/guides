from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class CloudModelError(RuntimeError):
    pass


class AccessDenied(CloudModelError):
    pass


class QuotaExceeded(CloudModelError):
    pass


class TenantInactive(CloudModelError):
    pass


@dataclass
class Event:
    event_id: str
    tenant_id: str
    document_id: str
    attempts: int = 0


class CloudModel:
    PLAN_LIMITS = {"starter": 2, "pro": 100}

    def __init__(self) -> None:
        self.tenants: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.outputs: dict[str, dict[str, Any]] = {}
        self.queue: list[Event] = []
        self.dead_letters: list[Event] = []
        self.processed_events: set[str] = set()
        self.usage: dict[str, int] = {}
        self.resources: list[dict[str, Any]] = []

    def provision_tenant(self, tenant_id: str, plan: str = "starter") -> None:
        if plan not in self.PLAN_LIMITS:
            raise ValueError(f"unknown plan: {plan}")
        if tenant_id in self.tenants and self.tenants[tenant_id]["state"] == "ACTIVE":
            raise CloudModelError(f"tenant already active: {tenant_id}")
        self.tenants[tenant_id] = {"state": "ACTIVE", "plan": plan}
        self.usage.setdefault(tenant_id, 0)
        self.resources.extend(
            [
                {"id": f"db-partition:{tenant_id}", "tenant_id": tenant_id, "type": "database", "stateful": True, "public": False},
                {"id": f"object-prefix:{tenant_id}", "tenant_id": tenant_id, "type": "object-prefix", "stateful": True, "public": False},
            ]
        )

    def _require_active(self, tenant_id: str) -> dict[str, Any]:
        tenant = self.tenants.get(tenant_id)
        if not tenant or tenant["state"] != "ACTIVE":
            raise TenantInactive(tenant_id)
        return tenant

    def store_document(self, tenant_id: str, document_id: str, content: str) -> None:
        tenant = self._require_active(tenant_id)
        existing = self.documents.get(document_id)
        if existing and existing["tenant_id"] != tenant_id:
            raise AccessDenied(document_id)
        is_new = existing is None
        if is_new:
            current = sum(1 for item in self.documents.values() if item["tenant_id"] == tenant_id)
            limit = self.PLAN_LIMITS[tenant["plan"]]
            if current >= limit:
                raise QuotaExceeded(f"{tenant_id}: {current}/{limit}")
        self.documents[document_id] = {"tenant_id": tenant_id, "content": content}

    def read_document(self, requester_tenant: str, document_id: str) -> str:
        self._require_active(requester_tenant)
        document = self.documents.get(document_id)
        if not document or document["tenant_id"] != requester_tenant:
            raise AccessDenied(document_id)
        return str(document["content"])

    def enqueue_event(self, event_id: str, tenant_id: str, document_id: str) -> None:
        self._require_active(tenant_id)
        self.queue.append(Event(event_id, tenant_id, document_id))

    def process_next(self, max_attempts: int = 2) -> str:
        if not self.queue:
            return "empty"
        event = self.queue.pop(0)
        if event.event_id in self.processed_events:
            return "duplicate"
        try:
            self._require_active(event.tenant_id)
            document = self.documents.get(event.document_id)
            if not document or document["tenant_id"] != event.tenant_id:
                raise CloudModelError("missing or mismatched document")
            output_id = f"result:{event.tenant_id}:{event.document_id}"
            self.outputs[output_id] = {
                "tenant_id": event.tenant_id,
                "document_id": event.document_id,
                "source_event": event.event_id,
            }
            self.usage[event.tenant_id] = self.usage.get(event.tenant_id, 0) + 1
            self.processed_events.add(event.event_id)
            return "processed"
        except CloudModelError:
            event.attempts += 1
            if event.attempts >= max_attempts:
                self.dead_letters.append(event)
                return "dead-lettered"
            self.queue.append(event)
            return "retry"

    def drain_events(self, max_attempts: int = 2, max_steps: int = 100) -> None:
        steps = 0
        while self.queue and steps < max_steps:
            self.process_next(max_attempts=max_attempts)
            steps += 1
        if self.queue:
            raise CloudModelError("event drain exceeded max_steps")

    def usage_for(self, tenant_id: str) -> int:
        return self.usage.get(tenant_id, 0)

    def delete_tenant(self, tenant_id: str) -> None:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return
        tenant["state"] = "DELETED"
        self.documents = {key: value for key, value in self.documents.items() if value["tenant_id"] != tenant_id}
        self.outputs = {key: value for key, value in self.outputs.items() if value["tenant_id"] != tenant_id}
        self.queue = [event for event in self.queue if event.tenant_id != tenant_id]
        self.resources = [resource for resource in self.resources if resource["tenant_id"] != tenant_id]

    def resource_inventory(self) -> list[dict[str, Any]]:
        return [dict(resource) for resource in self.resources]
