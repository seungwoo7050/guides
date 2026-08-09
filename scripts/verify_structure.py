#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from toolchain_contract import contract as toolchain_contract

ROOT = Path(__file__).resolve().parents[1]

CONCEPTS = [
    "docs/01-mobile-runtime-and-project-boundaries.md",
    "docs/02-layout-input-and-accessibility.md",
    "docs/03-navigation-links-and-state-restoration.md",
    "docs/04-networking-session-and-error-contracts.md",
    "docs/05-local-data-offline-and-sync.md",
    "docs/06-permissions-device-capabilities-and-privacy.md",
    "docs/07-background-work-notifications-and-lifecycle.md",
    "docs/08-native-boundary-kotlin-swift-and-builds.md",
    "docs/09-testing-performance-and-observability.md",
    "docs/10-release-signing-updates-and-store-delivery.md",
]

ROLE_PATHS = {
    "entrypoint": ["README.md"],
    "scope-roadmap": ["docs/00-roadmap-and-prerequisites.md"],
    "concept-path": CONCEPTS,
    "practical-transition": ["docs/90-practical-checklist.md"],
    "step-practice": [
        f"exercises/field-notes/specs/{number:02d}-{name}.md"
        for number, name in enumerate(
            [
                "runtime-navigation",
                "offline-records",
                "media-permissions",
                "sync-conflicts",
                "background-notifications",
                "quality-release",
            ],
            start=1,
        )
    ],
    "incomplete-start": [
        "exercises/field-notes/skeleton/package.json",
        "exercises/field-notes/skeleton/README.md",
    ],
    "runnable-reference": [
        "exercises/field-notes/reference/package.json",
        "exercises/field-notes/reference/README.md",
        "exercises/field-notes/fault-server/package.json",
        "exercises/field-notes/sync-engine/package.json",
        "exercises/field-notes/lifecycle-engine/package.json",
    ],
    "release-profile-and-evidence-contract": [
        "exercises/field-notes/reference/eas.json",
        "exercises/field-notes/release-contract/package.json",
        "exercises/field-notes/release-contract/README.md",
    ],
    "public-contract": [
        "exercises/field-notes/shared/src/contracts.ts",
        "exercises/field-notes/shared/src/ports.ts",
        "exercises/field-notes/shared/src/testkit.ts",
    ],
    "expected-evidence": [
        "exercises/field-notes/checks/acceptance-matrix.md",
        "exercises/field-notes/checks/evidence-template.md",
        "exercises/field-notes/checks/manual-device-matrix.md",
    ],
    "cumulative-capstone": [
        "capstone/README.md",
        "capstone/architecture-contract.md",
        "capstone/data-sync-contract.md",
        "capstone/device-test-matrix.md",
        "capstone/release-evidence.md",
    ],
    "reproduction": [
        "package.json",
        "package-lock.json",
        "prepare.sh",
        "verify.sh",
        "scripts/process_runner.py",
        "scripts/source_manifest.py",
        "scripts/source_fingerprint.py",
        "scripts/dependency_receipt.py",
        "scripts/workspace_contract.py",
    ],
    "maintenance": ["CONTRIBUTING.md", "reference/official-sources.md"],
}

OWNS = [
    "모바일 앱 수명 주기와 navigation",
    "오프라인 캐시·동기화",
    "카메라·위치·알림·background 작업",
    "Android·iOS 빌드·서명·배포",
    "네이티브 모듈 경계 읽기",
]
EXCLUDES = ["Kotlin·Swift 언어 전체", "네이티브 Android·iOS 전문 트랙", "모바일 백엔드 운영"]
EXITS = [
    "Android·iOS에서 동작하는 앱을 만든다",
    "오프라인·권한·기기 기능 실패를 처리한다",
    "실제 빌드와 배포 산출물을 검증한다",
]


def fail(message: str) -> None:
    raise SystemExit(f"STRUCTURE ERROR: {message}")


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        fail(f"필수 역할 파일 누락: {relative}")
    text = path.read_text()
    if not text.strip():
        fail(f"빈 역할 파일: {relative}")
    return text


def main() -> None:
    for role, paths in ROLE_PATHS.items():
        for relative in paths:
            read(relative)

    readme = read("README.md")
    roadmap = read("docs/00-roadmap-and-prerequisites.md")
    for phrase in OWNS:
        if phrase not in readme or phrase not in roadmap:
            fail(f"catalog owns가 entrypoint/roadmap에 고정되지 않았습니다: {phrase}")
    for phrase in EXCLUDES:
        if phrase not in readme or phrase not in roadmap:
            fail(f"catalog excludes가 누락됐습니다: {phrase}")
    for phrase in EXITS:
        if phrase not in readme or phrase not in roadmap:
            fail(f"catalog exit capability가 누락됐습니다: {phrase}")

    for phrase in ("대상 독자", "학습 순서", "종료 능력", "가이드 이후"):
        if phrase not in readme:
            fail(f"README 탐색 역할 누락: {phrase}")
    for phrase in ("owns에서 exit capability까지의 추적", "대표 실패", "다음 프로젝트 경로"):
        if phrase not in roadmap:
            fail(f"roadmap 추적 역할 누락: {phrase}")

    concept_text = "\n".join(read(path) for path in CONCEPTS)
    for concept in CONCEPTS:
        text = read(concept)
        if "## 목표" not in text or "Stage" not in text:
            fail(f"개념→학습 결과/실습 연결 누락: {concept}")
    for token in ("소유", "사건", "정상", "경계", "실패", "불변식", "검증", "보장하지", "비소유"):
        if token not in concept_text:
            fail(f"개념 경로 전체의 품질 질문 누락: {token}")

    capstone = read("capstone/README.md")
    for token in ("필수 통합 failure journey", "사람 검토 질문", "알려진 한계"):
        if token not in capstone:
            fail(f"capstone 역할 누락: {token}")
    for gate in range(1, 6):
        if f"Gate {gate}" not in capstone:
            fail(f"capstone Gate {gate} 누락")

    package = json.loads(read("package.json"))
    toolchain = toolchain_contract()
    if package.get("packageManager") != f"npm@{toolchain['npm']}":
        fail("npm 재현 pin이 packageManager에 없습니다.")
    engines = package.get("engines", {})
    if engines.get("node") != toolchain["nodeEngine"] or engines.get("npm") != toolchain["npmEngine"]:
        fail("Node/npm 재현 engine 범위가 기준 pin과 다릅니다.")
    workspaces = set(package.get("workspaces", []))
    required_workspaces = {
        "exercises/field-notes/fault-server",
        "exercises/field-notes/lifecycle-engine",
        "exercises/field-notes/release-contract",
        "exercises/field-notes/shared",
        "exercises/field-notes/skeleton",
        "exercises/field-notes/reference",
        "exercises/field-notes/sync-engine",
    }
    if workspaces != required_workspaces:
        fail(
            "Field Notes workspace 집합 불일치: "
            f"missing={sorted(required_workspaces - workspaces)} "
            f"unexpected={sorted(workspaces - required_workspaces)}"
        )

    scripts = package.get("scripts", {})
    if not isinstance(scripts, dict):
        fail("root package scripts가 object가 아닙니다.")
    required_scripts = {
        "typecheck",
        "test:reference",
        "test:skeleton:reject",
        "test:mutants",
        "check:cng",
        "check:expo",
        "verify",
    }
    missing_scripts = required_scripts - set(scripts)
    if missing_scripts:
        fail(f"verify command graph script 누락: {sorted(missing_scripts)}")

    for relative in ("prepare.sh", "verify.sh", "scripts/source_fingerprint.py"):
        if not ((ROOT / relative).stat().st_mode & os.X_OK):
            fail(f"실행 권한 누락: {relative}")

    roles = ",".join(ROLE_PATHS)
    print(f"MECHANICAL STRUCTURE OK roles={len(ROLE_PATHS)} concepts={len(CONCEPTS)} [{roles}]")
    print("STRUCTURE LIMIT: heading/token presence does not prove educational quality or stable status")


if __name__ == "__main__":
    main()
