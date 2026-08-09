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


class EventConflict(CloudModelError):
    pass


@dataclass
class Event:
    event_id: str
    tenant_id: str
    document_id: str
    attempts: int = 0


class CloudModel:
    """Deterministic model of the guide's public cloud/SaaS invariants.

    Document quota is active document capacity, not a monthly usage counter.
    Event identity is scoped to a tenant: ``(tenant_id, event_id)``.
    """

    PLAN_LIMITS = {"starter": 2, "pro": 100}

    def __init__(self) -> None:
        self.tenants: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.outputs: dict[str, dict[str, Any]] = {}
        self.queue: list[Event] = []
        self.dead_letters: list[Event] = []
        self.event_registry: dict[tuple[str, str], str] = {}
        self.processed_events: set[tuple[str, str]] = set()
        self.usage: dict[str, int] = {}
        self.resources: list[dict[str, Any]] = []

    def provision_tenant(self, tenant_id: str, plan: str = "starter") -> None:
        if plan not in self.PLAN_LIMITS:
            raise ValueError(f"unknown plan: {plan}")
        existing = self.tenants.get(tenant_id)
        if existing:
            if existing["state"] == "DELETED":
                raise TenantInactive(f"tenant id cannot be reused: {tenant_id}")
            raise CloudModelError(f"tenant already active: {tenant_id}")
        self.tenants[tenant_id] = {"state": "ACTIVE", "plan": plan}
        self.usage[tenant_id] = 0
        self.resources.extend(
            [
                {
                    "id": f"db-partition:{tenant_id}",
                    "tenant_id": tenant_id,
                    "type": "database",
                    "stateful": True,
                    "public": False,
                },
                {
                    "id": f"object-prefix:{tenant_id}",
                    "tenant_id": tenant_id,
                    "type": "object-prefix",
                    "stateful": True,
                    "public": False,
                },
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
        if existing is None:
            active_count = sum(
                1 for document in self.documents.values() if document["tenant_id"] == tenant_id
            )
            capacity = self.PLAN_LIMITS[tenant["plan"]]
            if active_count >= capacity:
                raise QuotaExceeded(f"{tenant_id}: {active_count}/{capacity}")
        self.documents[document_id] = {"tenant_id": tenant_id, "content": content}

    def read_document(self, requester_tenant: str, document_id: str) -> str:
        self._require_active(requester_tenant)
        document = self.documents.get(document_id)
        if not document or document["tenant_id"] != requester_tenant:
            raise AccessDenied(document_id)
        return str(document["content"])

    def enqueue_event(self, event_id: str, tenant_id: str, document_id: str) -> None:
        self._require_active(tenant_id)
        identity = (tenant_id, event_id)
        registered_document = self.event_registry.get(identity)
        if registered_document is not None and registered_document != document_id:
            raise EventConflict(f"event payload changed: {tenant_id}/{event_id}")
        self.event_registry.setdefault(identity, document_id)
        self.queue.append(Event(event_id, tenant_id, document_id))

    def process_next(self, max_attempts: int = 2) -> str:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if not self.queue:
            return "empty"
        event = self.queue.pop(0)
        identity = (event.tenant_id, event.event_id)
        if identity in self.processed_events:
            return "duplicate"
        try:
            self._require_active(event.tenant_id)
            document = self.documents.get(event.document_id)
            if not document or document["tenant_id"] != event.tenant_id:
                raise CloudModelError("missing or mismatched document")
            output_id = f"result:{event.tenant_id}:{event.document_id}:{event.event_id}"
            self.outputs[output_id] = {
                "tenant_id": event.tenant_id,
                "document_id": event.document_id,
                "source_event": event.event_id,
            }
            self.usage[event.tenant_id] = self.usage.get(event.tenant_id, 0) + 1
            self.processed_events.add(identity)
            return "processed"
        except CloudModelError:
            event.attempts += 1
            if event.attempts >= max_attempts:
                self.dead_letters.append(event)
                return "dead-lettered"
            self.queue.append(event)
            return "retry"

    def drain_events(self, max_attempts: int = 2, max_steps: int = 100) -> None:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if max_steps <= 0:
            raise ValueError("max_steps must be positive")
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
        if not tenant or tenant["state"] == "DELETED":
            return
        tenant["state"] = "DELETED"
        self.documents = {
            key: value for key, value in self.documents.items() if value["tenant_id"] != tenant_id
        }
        self.outputs = {
            key: value for key, value in self.outputs.items() if value["tenant_id"] != tenant_id
        }
        self.queue = [event for event in self.queue if event.tenant_id != tenant_id]
        self.dead_letters = [event for event in self.dead_letters if event.tenant_id != tenant_id]
        tenant_event_ids = {
            identity for identity in self.event_registry if identity[0] == tenant_id
        }
        for identity in tenant_event_ids:
            del self.event_registry[identity]
        self.processed_events.difference_update(tenant_event_ids)
        self.resources = [
            resource for resource in self.resources if resource["tenant_id"] != tenant_id
        ]

    def resource_inventory(self) -> list[dict[str, Any]]:
        return [dict(resource) for resource in sorted(self.resources, key=lambda item: item["id"])]

    def evidence_snapshot(self, tenant_id: str) -> dict[str, Any]:
        """Return deterministic, content-free evidence for one tenant.

        The DELETED tombstone and aggregate usage are retained evidence. Active
        documents, outputs, events, processing state and resources are not.
        """

        tenant = self.tenants.get(tenant_id)
        documents = sorted(
            document_id
            for document_id, value in self.documents.items()
            if value["tenant_id"] == tenant_id
        )
        outputs = sorted(
            output_id
            for output_id, value in self.outputs.items()
            if value["tenant_id"] == tenant_id
        )
        pending = sorted(
            (
                {
                    "event_id": event.event_id,
                    "document_id": event.document_id,
                    "attempts": event.attempts,
                }
                for event in self.queue
                if event.tenant_id == tenant_id
            ),
            key=lambda item: (item["event_id"], item["document_id"], item["attempts"]),
        )
        dead_letters = sorted(
            (
                {
                    "event_id": event.event_id,
                    "document_id": event.document_id,
                    "attempts": event.attempts,
                }
                for event in self.dead_letters
                if event.tenant_id == tenant_id
            ),
            key=lambda item: (item["event_id"], item["document_id"], item["attempts"]),
        )
        event_registry = sorted(
            (
                {
                    "event_id": event_id,
                    "document_id": document_id,
                    "processed": (registered_tenant, event_id) in self.processed_events,
                }
                for (registered_tenant, event_id), document_id in self.event_registry.items()
                if registered_tenant == tenant_id
            ),
            key=lambda item: item["event_id"],
        )
        resources = [
            resource
            for resource in self.resource_inventory()
            if resource["tenant_id"] == tenant_id
        ]
        return {
            "tenant_id": tenant_id,
            "tenant": dict(tenant) if tenant is not None else None,
            "active_documents": documents,
            "active_outputs": outputs,
            "pending_events": pending,
            "dead_letters": dead_letters,
            "event_registry": event_registry,
            "resources": resources,
            "usage_evidence": self.usage_for(tenant_id),
        }
