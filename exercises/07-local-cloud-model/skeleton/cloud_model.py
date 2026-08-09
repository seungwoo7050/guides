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
        self.tenants[tenant_id] = {"state": "ACTIVE", "plan": plan}
        self.usage.setdefault(tenant_id, 0)
        # 잘못된 시작 상태: stateful resource가 public입니다.
        self.resources.append({"id": f"db:{tenant_id}", "tenant_id": tenant_id, "type": "database", "stateful": True, "public": True})

    def _require_active(self, tenant_id: str) -> dict[str, Any]:
        tenant = self.tenants.get(tenant_id)
        if not tenant or tenant["state"] != "ACTIVE":
            raise TenantInactive(tenant_id)
        return tenant

    def store_document(self, tenant_id: str, document_id: str, content: str) -> None:
        tenant = self._require_active(tenant_id)
        # 잘못된 시작 상태: 먼저 write한 뒤 quota를 검사해 partial state를 남깁니다.
        self.documents[document_id] = {"tenant_id": tenant_id, "content": content}
        current = sum(1 for item in self.documents.values() if item["tenant_id"] == tenant_id)
        if current > self.PLAN_LIMITS[tenant["plan"]]:
            raise QuotaExceeded(tenant_id)

    def read_document(self, requester_tenant: str, document_id: str) -> str:
        self._require_active(requester_tenant)
        # 잘못된 시작 상태: document owner를 검사하지 않습니다.
        document = self.documents[document_id]
        return str(document["content"])

    def enqueue_event(self, event_id: str, tenant_id: str, document_id: str) -> None:
        self.queue.append(Event(event_id, tenant_id, document_id))

    def process_next(self, max_attempts: int = 2) -> str:
        if not self.queue:
            return "empty"
        event = self.queue.pop(0)
        document = self.documents.get(event.document_id)
        if not document:
            event.attempts += 1
            if event.attempts >= max_attempts:
                self.dead_letters.append(event)
                return "dead-lettered"
            self.queue.append(event)
            return "retry"
        # 잘못된 시작 상태: duplicate event를 처리하고 usage를 다시 증가시킵니다.
        output_id = f"result:{event.tenant_id}:{event.document_id}:{event.event_id}:{self.usage.get(event.tenant_id, 0)}"
        self.outputs[output_id] = {"tenant_id": event.tenant_id, "document_id": event.document_id}
        self.usage[event.tenant_id] = self.usage.get(event.tenant_id, 0) + 1
        return "processed"

    def drain_events(self, max_attempts: int = 2, max_steps: int = 100) -> None:
        steps = 0
        while self.queue and steps < max_steps:
            self.process_next(max_attempts=max_attempts)
            steps += 1

    def usage_for(self, tenant_id: str) -> int:
        return self.usage.get(tenant_id, 0)

    def delete_tenant(self, tenant_id: str) -> None:
        if tenant_id in self.tenants:
            self.tenants[tenant_id]["state"] = "DELETED"
        # 잘못된 시작 상태: documents, queue, outputs와 resources를 남깁니다.

    def resource_inventory(self) -> list[dict[str, Any]]:
        return [dict(resource) for resource in self.resources]
