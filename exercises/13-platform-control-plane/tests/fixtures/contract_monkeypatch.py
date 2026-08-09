"""Attack fixture: replace the in-process public contract and expose dummy APIs."""

from __future__ import annotations

import sys


contract = sys.modules.get("platform_public_contract")
if contract is not None:
    identifiers = {
        "service_id": "svc-payments",
        "resource_id": "env-payments-staging",
        "operation_id": "op-payments-staging-v3",
        "tenant_id": "tenant-checkout",
        "artifact_id": "sha256:" + "a" * 64,
        "profile_id": "stateless-http/v3",
    }
    contract.run_contract = lambda module: [
        {
            "id": f"PE-{index:03d}",
            "kind": "forged",
            "title": "forged",
            "status": "pass",
            "message": "forged",
            "observed": {"identifiers": identifiers} if index == 1 else {},
        }
        for index in range(1, 11)
    ]


def _dummy(*args, **kwargs):
    return {"state": {}, "result": {"status": "Ready"}}


request_environment = _dummy
reconcile = _dummy
observe_drift = _dummy
request_migration = _dummy
retire_service = _dummy
snapshot = _dummy
