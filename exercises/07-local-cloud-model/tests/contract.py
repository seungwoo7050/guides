from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable


class ContractAssertion(AssertionError):
    pass


@dataclass(frozen=True)
class Check:
    id: str
    kind: str
    title: str
    run: Callable[[Any], dict[str, Any]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractAssertion(message)


def snapshot(model: Any, tenant_id: str) -> dict[str, Any]:
    value = model.evidence_snapshot(tenant_id)
    require(isinstance(value, dict), "evidence_snapshot must return an object")
    json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def snapshot_sha256(value: dict[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def result(model: Any, tenant_id: str, **observed: Any) -> dict[str, Any]:
    evidence = snapshot(model, tenant_id)
    return {"evidence_sha256": snapshot_sha256(evidence), "observed": observed}


def expect_exception(exception_type: type[BaseException], action: Callable[[], Any]) -> None:
    try:
        action()
    except exception_type:
        return
    except Exception as error:  # noqa: BLE001 - contract reports the actual public exception
        raise ContractAssertion(
            f"expected {exception_type.__name__}, got {type(error).__name__}"
        ) from error
    raise ContractAssertion(f"expected {exception_type.__name__}")


def provision_pair(module: Any) -> Any:
    model = module.CloudModel()
    model.provision_tenant("tenant-a", "starter")
    model.provision_tenant("tenant-b", "starter")
    return model


def cm_001(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    evidence = snapshot(model, "tenant-a")
    resources = evidence["resources"]
    require(len(resources) == 2, "tenant must own two stateful resources")
    require(all(item["stateful"] is True for item in resources), "resources must be stateful")
    require(all(item["public"] is False for item in resources), "stateful resources must be private")
    require(len({item["id"] for item in resources}) == 2, "resource identities must be unique")
    return result(model, "tenant-a", resource_count=len(resources), all_private=True)


def cm_002(module: Any) -> dict[str, Any]:
    model = module.CloudModel()
    model.provision_tenant("tenant-a", "starter")
    before = snapshot(model, "tenant-a")
    expect_exception(ValueError, lambda: model.provision_tenant("tenant-b", "unknown"))
    expect_exception(module.CloudModelError, lambda: model.provision_tenant("tenant-a", "pro"))
    after = snapshot(model, "tenant-a")
    require(after == before, "failed provisioning must not change the active tenant")
    require(snapshot(model, "tenant-b")["tenant"] is None, "invalid plan must not create a tenant")
    return result(model, "tenant-a", active_plan=after["tenant"]["plan"], unchanged=True)


def cm_003(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-1", "one")
    model.store_document("tenant-a", "doc-2", "two")
    model.store_document("tenant-a", "doc-2", "updated")
    require(model.read_document("tenant-a", "doc-2") == "updated", "owner update must remain readable")
    evidence = snapshot(model, "tenant-a")
    require(evidence["active_documents"] == ["doc-1", "doc-2"], "update must not consume capacity")
    return result(model, "tenant-a", active_document_count=2, owner_read="updated")


def cm_004(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-a", "synthetic-secret")
    before = snapshot(model, "tenant-a")
    expect_exception(module.AccessDenied, lambda: model.read_document("tenant-b", "doc-a"))
    expect_exception(module.AccessDenied, lambda: model.read_document("tenant-b", "missing"))
    after = snapshot(model, "tenant-a")
    require(after == before, "denied reads must not mutate protected state")
    return result(model, "tenant-a", foreign_denied=True, missing_denied=True, unchanged=True)


def cm_005(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-1", "one")
    model.store_document("tenant-a", "doc-2", "two")
    before = snapshot(model, "tenant-a")
    expect_exception(
        module.QuotaExceeded,
        lambda: model.store_document("tenant-a", "doc-3", "three"),
    )
    after = snapshot(model, "tenant-a")
    require(after == before, "quota rejection must be atomic")
    require("doc-3" not in after["active_documents"], "rejected document must not remain active")
    return result(model, "tenant-a", capacity=2, active_document_count=2, partial_write=False)


def cm_006(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-a", "data")
    model.enqueue_event("event-1", "tenant-a", "doc-a")
    model.enqueue_event("event-1", "tenant-a", "doc-a")
    model.enqueue_event("event-2", "tenant-a", "doc-a")
    statuses = [model.process_next(), model.process_next(), model.process_next()]
    evidence = snapshot(model, "tenant-a")
    require(statuses == ["processed", "duplicate", "processed"], "duplicate and distinct deliveries must differ")
    require(len(evidence["active_outputs"]) == 2, "two distinct events must create two distinct outputs")
    require(evidence["usage_evidence"] == 2, "duplicate must not increment usage")
    return result(model, "tenant-a", statuses=statuses, output_count=2, usage=2)


def cm_007(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-a", "a")
    model.store_document("tenant-a", "doc-a2", "a2")
    model.store_document("tenant-b", "doc-b", "b")
    model.enqueue_event("shared-id", "tenant-a", "doc-a")
    model.enqueue_event("shared-id", "tenant-b", "doc-b")
    before = snapshot(model, "tenant-a")
    expect_exception(
        module.EventConflict,
        lambda: model.enqueue_event("shared-id", "tenant-a", "doc-a2"),
    )
    require(snapshot(model, "tenant-a") == before, "conflicting event must not change tenant-a queue")
    statuses = [model.process_next(), model.process_next()]
    evidence_a = snapshot(model, "tenant-a")
    evidence_b = snapshot(model, "tenant-b")
    require(statuses == ["processed", "processed"], "same event ID must be independent across tenants")
    require(evidence_a["usage_evidence"] == 1 and evidence_b["usage_evidence"] == 1, "tenant-scoped events need independent usage")
    return result(model, "tenant-a", statuses=statuses, tenant_a_usage=1, tenant_b_usage=1)


def cm_008(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.enqueue_event("missing-1", "tenant-a", "missing")
    require(model.process_next(max_attempts=2) == "retry", "first failure must retry")
    interim = snapshot(model, "tenant-a")
    require(interim["pending_events"][0]["attempts"] == 1, "retry attempt must be observable")
    require(model.process_next(max_attempts=2) == "dead-lettered", "second failure must dead-letter")
    final = snapshot(model, "tenant-a")
    require(final["dead_letters"][0]["attempts"] == 2, "dead letter must record exact attempts")
    require(final["usage_evidence"] == 0 and not final["active_outputs"], "failed event must have no effect")

    one_try = provision_pair(module)
    one_try.enqueue_event("missing-2", "tenant-a", "missing")
    require(one_try.process_next(max_attempts=1) == "dead-lettered", "max_attempts=1 must dead-letter immediately")
    before_invalid = snapshot(one_try, "tenant-a")
    expect_exception(ValueError, lambda: one_try.process_next(max_attempts=0))
    require(snapshot(one_try, "tenant-a") == before_invalid, "invalid attempt limit must not mutate state")
    return result(model, "tenant-a", attempts=2, dead_letter_count=1, usage=0)


def cm_009(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-a", "protected")
    model.enqueue_event("event-b", "tenant-b", "doc-a")
    model.drain_events(max_attempts=2)
    evidence_a = snapshot(model, "tenant-a")
    evidence_b = snapshot(model, "tenant-b")
    require(not evidence_b["active_outputs"], "foreign event must not create tenant-b output")
    require(evidence_b["usage_evidence"] == 0, "foreign event must not create usage")
    require(len(evidence_b["dead_letters"]) == 1, "foreign event must terminate in dead letter")
    require(evidence_a["active_documents"] == ["doc-a"], "foreign event must not mutate owner document")
    return result(model, "tenant-b", output_count=0, usage=0, dead_letter_count=1)


def cm_010(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.enqueue_event("missing", "tenant-a", "missing")
    expect_exception(
        module.CloudModelError,
        lambda: model.drain_events(max_attempts=3, max_steps=1),
    )
    evidence = snapshot(model, "tenant-a")
    require(len(evidence["pending_events"]) == 1, "bounded drain must preserve pending event")
    require(evidence["pending_events"][0]["attempts"] == 1, "bounded drain must preserve attempt evidence")
    return result(model, "tenant-a", pending_count=1, attempts=1, bound_reported=True)


def cm_011(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-a", "data")
    model.enqueue_event("processed", "tenant-a", "doc-a")
    require(model.process_next() == "processed", "setup event must process")
    model.enqueue_event("pending", "tenant-a", "missing")
    model.enqueue_event("dead", "tenant-a", "missing")
    require(model.process_next(max_attempts=2) == "retry", "pending setup must retry")
    require(model.process_next(max_attempts=1) == "dead-lettered", "dead-letter setup must terminate")
    usage_before = model.usage_for("tenant-a")
    model.delete_tenant("tenant-a")
    evidence = snapshot(model, "tenant-a")
    require(evidence["tenant"] == {"state": "DELETED", "plan": "starter"}, "deleted tombstone must remain")
    for field in (
        "active_documents",
        "active_outputs",
        "pending_events",
        "dead_letters",
        "event_registry",
        "resources",
    ):
        require(evidence[field] == [], f"deletion must clear {field}")
    require(evidence["usage_evidence"] == usage_before == 1, "documented usage evidence must remain")
    require(snapshot(model, "tenant-b")["tenant"]["state"] == "ACTIVE", "other tenant must remain active")
    expect_exception(module.TenantInactive, lambda: model.read_document("tenant-a", "doc-a"))
    expect_exception(module.TenantInactive, lambda: model.enqueue_event("late", "tenant-a", "doc-a"))
    return result(model, "tenant-a", tombstone="DELETED", usage_retained=1, active_state_cleared=True)


def cm_012(module: Any) -> dict[str, Any]:
    model = module.CloudModel()
    model.provision_tenant("tenant-a", "starter")
    model.delete_tenant("tenant-a")
    first = snapshot(model, "tenant-a")
    model.delete_tenant("tenant-a")
    require(snapshot(model, "tenant-a") == first, "repeated deletion must be idempotent")
    expect_exception(module.TenantInactive, lambda: model.provision_tenant("tenant-a", "pro"))
    require(snapshot(model, "tenant-a") == first, "deleted tenant ID reuse must not mutate evidence")
    unknown_before = snapshot(model, "unknown")
    model.delete_tenant("unknown")
    require(snapshot(model, "unknown") == unknown_before, "unknown deletion must be a no-op")
    return result(model, "tenant-a", idempotent=True, reuse_rejected=True)


def cm_013(module: Any) -> dict[str, Any]:
    model = provision_pair(module)
    model.store_document("tenant-a", "doc-a", "must-not-appear")
    first = snapshot(model, "tenant-a")
    serialized = json.dumps(first, ensure_ascii=False, sort_keys=True)
    require("must-not-appear" not in serialized, "evidence must not expose document content")
    first["active_documents"].append("tampered")
    second = snapshot(model, "tenant-a")
    require("tampered" not in second["active_documents"], "snapshot must not alias model state")
    require(second == snapshot(model, "tenant-a"), "snapshot must be deterministic")
    return result(model, "tenant-a", content_exposed=False, deep_copy=True, deterministic=True)


CHECKS = (
    Check("CM-001", "normal-safety", "stateful resources are private", cm_001),
    Check("CM-002", "boundary", "tenant provisioning rejects invalid transitions", cm_002),
    Check("CM-003", "normal-boundary", "owner update preserves active document capacity", cm_003),
    Check("CM-004", "failure-isolation", "foreign and missing reads are denied", cm_004),
    Check("CM-005", "boundary-failure", "active document quota rejection is atomic", cm_005),
    Check("CM-006", "delivery-failure", "duplicates have one effect and distinct events have distinct outputs", cm_006),
    Check("CM-007", "delivery-boundary", "event identity is tenant scoped and payload stable", cm_007),
    Check("CM-008", "failure-boundary", "retry and dead-letter attempt bounds are exact", cm_008),
    Check("CM-009", "failure-isolation", "event processing enforces document tenant", cm_009),
    Check("CM-010", "failure-safety", "bounded drain reports remaining work", cm_010),
    Check("CM-011", "cleanup", "tenant deletion clears active state and retains evidence", cm_011),
    Check("CM-012", "lifecycle-boundary", "deleted tenant identity is terminal", cm_012),
    Check("CM-013", "evidence", "evidence snapshot is safe and deterministic", cm_013),
)


def run_contract(module: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for check in CHECKS:
        record: dict[str, Any] = {
            "id": check.id,
            "kind": check.kind,
            "title": check.title,
            "status": "pass",
            "message": "contract satisfied",
            "evidence_sha256": None,
            "observed": {},
        }
        try:
            evidence = check.run(module)
            record["evidence_sha256"] = evidence["evidence_sha256"]
            record["observed"] = evidence["observed"]
        except ContractAssertion as error:
            record["status"] = "fail"
            record["message"] = str(error)
        except Exception as error:  # noqa: BLE001 - public learner API failures are reported
            record["status"] = "error"
            record["message"] = f"{type(error).__name__}: {error}"
        results.append(record)
    return results
