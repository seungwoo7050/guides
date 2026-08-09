#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    'README.md', 'CONTRIBUTING.md', 'LICENSE.md', 'Makefile',
    'prepare.sh', 'verify.sh',
    'docs/00-roadmap.md',
    'docs/01-cloud-state-responsibility-and-evidence.md',
    'docs/02-cloud-characteristics-service-and-deployment-models.md',
    'docs/03-control-plane-data-plane-and-identity.md',
    'docs/04-iaas-compute-network-and-storage.md',
    'docs/05-failure-domains-elasticity-and-recovery.md',
    'docs/06-paas-and-managed-service-contracts.md',
    'docs/07-serverless-and-faas-runtime.md',
    'docs/08-event-delivery-concurrency-and-idempotency.md',
    'docs/09-saas-tenancy-and-isolation.md',
    'docs/10-saas-entitlements-metering-and-billing.md',
    'docs/11-cloud-security-observability-and-incidents.md',
    'docs/12-cost-capacity-quotas-and-finops.md',
    'docs/13-portability-lock-in-and-exit.md',
    'docs/14-service-selection-and-architecture-review.md',
    'docs/15-capstone.md',
    'docs/90-standards-map.md',
    'exercises/README.md',
    'projects/multitenant-document-processing-saas/README.md',
    'reference/glossary.md',
    'reference/responsibility-matrix.md',
    'reference/architecture-review-checklist.md',
    'reference/cloud-experiment-safety.md',
    'reference/provider-crosswalk.md',
    'reference/command-reference.md',
    'profiles/README.md',
]
DOCUMENT_EXERCISES = [
    '01-service-classification',
    '02-iaas-failure-domains',
    '03-managed-service-contract',
    '04-faas-event-lifecycle',
    '05-saas-tenant-isolation',
    '06-cost-and-exit',
]


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f'missing required file: {relative}')
    for exercise in DOCUMENT_EXERCISES:
        base = ROOT / 'exercises' / exercise
        for relative in ('README.md', 'contract.json'):
            if not (base / relative).is_file():
                errors.append(f'{exercise}: missing {relative}')
        for profile in ('template', 'reference'):
            if not (base / profile).is_dir():
                errors.append(f'{exercise}: missing {profile}/')
        if (base / 'contract.json').is_file():
            try:
                contract = json.loads((base / 'contract.json').read_text(encoding='utf-8'))
            except json.JSONDecodeError as exc:
                errors.append(f'{exercise}/contract.json: {exc}')
            else:
                if not contract.get('required_files'):
                    errors.append(f'{exercise}/contract.json: required_files empty')
    model = ROOT / 'exercises' / '07-local-cloud-model'
    for relative in ('README.md', 'skeleton/cloud_model.py', 'reference/cloud_model.py', 'tests/test_cloud_model.py'):
        if not (model / relative).is_file():
            errors.append(f'07-local-cloud-model: missing {relative}')
    project = ROOT / 'projects' / 'multitenant-document-processing-saas'
    for relative in ('contract.json', 'template', 'reference', 'inputs/system-brief.md', 'rubric.md'):
        if not (project / relative).exists():
            errors.append(f'capstone: missing {relative}')
    if errors:
        for error in errors:
            print(f'ERROR: {error}', file=sys.stderr)
        return 1
    print(f'structure OK: {len(REQUIRED)} required files, {len(DOCUMENT_EXERCISES)} document exercises')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
