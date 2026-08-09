#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "exercises/field-notes/specs"
EXPECTED = [
    "01-runtime-navigation.md",
    "02-offline-records.md",
    "03-media-permissions.md",
    "04-sync-conflicts.md",
    "05-background-notifications.md",
    "06-quality-release.md",
]
REQUIRED_SECTION_GROUPS = [
    ("## 목적", "## 학습 결과"),
    ("## 시작 상태",),
    ("## 실패 주입", "failure matrix", "대표 실패 시나리오", "## 누적 failure gate"),
    ("## 제출 증거", "## 제출 evidence"),
    ("## 비범위",),
    ("## 완료 조건", "## 완료 기준"),
]


def fail(message: str) -> None:
    raise SystemExit(f"EXERCISE ERROR: {message}")


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        fail(f"파일 누락: {relative}")
    return path.read_text()


def main() -> None:
    names = sorted(path.name for path in SPEC_DIR.glob("*.md"))
    if names != EXPECTED:
        fail(f"Stage 01~06 spec 목록 불일치: actual={names}")

    exercise_readme = read("exercises/field-notes/README.md")
    for index, name in enumerate(EXPECTED, start=1):
        relative = f"exercises/field-notes/specs/{name}"
        text = read(relative)
        if f"Stage {index:02d}" not in text:
            fail(f"Stage 번호 누락: {name}")
        for alternatives in REQUIRED_SECTION_GROUPS:
            if not any(section in text for section in alternatives):
                fail(f"{name}: 학습 계약 section 누락 {alternatives}")
        for token in ("미완성", "정상", "경계", "실패", "자동", "보장하지"):
            if token not in text:
                fail(f"{name}: 행동/evidence 계약 누락 {token}")
        if not any(token in text for token in ("실제 기기", "실제 Android/iOS", "device evidence")):
            fail(f"{name}: 실제 기기/양 platform evidence 계약 누락")
        if name not in exercise_readme:
            fail(f"Field Notes README가 spec을 연결하지 않습니다: {name}")

    stage_contracts = {
        "01-runtime-navigation.md": ("cold", "malformed", "process"),
        "02-offline-records.md": ("transaction", "migration", "outbox"),
        "03-media-permissions.md": ("camera", "picker", "location"),
        "04-sync-conflicts.md": ("commandId", "response loss", "version regression"),
        "05-background-notifications.md": ("bounded", "channel", "notification"),
        "06-quality-release.md": ("native-boundary", "artifact", "미검사"),
    }
    for name, tokens in stage_contracts.items():
        text = read(f"exercises/field-notes/specs/{name}")
        for token in tokens:
            if token.lower() not in text.lower():
                fail(f"{name}: 대표 공개 계약 누락 {token}")

    skeleton_text = "\n".join(
        path.read_text(errors="replace")
        for path in (ROOT / "exercises/field-notes/skeleton").rglob("*")
        if path.is_file() and path.suffix in {".ts", ".tsx", ".md"}
    )
    if skeleton_text.count("TODO") < 3 or "의도적으로 미완성" not in skeleton_text:
        fail("skeleton의 시작 상태와 의도적 미완성이 명확하지 않습니다.")

    contracts = read("exercises/field-notes/shared/src/contracts.ts")
    ports = read("exercises/field-notes/shared/src/ports.ts")
    for token in (
        "RecordSyncState",
        "RecordCommand",
        "RecordConflict",
        "CapabilityAvailability",
        "PermissionState",
        "NavigationIntent",
    ):
        if token not in contracts:
            fail(f"공개 contract type 누락: {token}")
    for token in (
        "RecordRepository",
        "AttachmentFileStore",
        "AttachmentRepository",
        "SessionStore",
        "SyncTransport",
        "PhotoPickerPort",
        "CameraPort",
        "LocationPort",
        "BackgroundScheduler",
        "NotificationPort",
        "NavigationIntentPort",
    ):
        if token not in ports:
            fail(f"누적 public port 누락: {token}")

    checks = "\n".join(
        read(f"exercises/field-notes/checks/{name}")
        for name in ("acceptance-matrix.md", "evidence-template.md", "manual-device-matrix.md")
    )
    for token in ("자동", "사람", "증거", "보장하지", "미검사"):
        if token not in checks:
            fail(f"자동/사람 evidence 구분 누락: {token}")

    capstone = read("capstone/README.md")
    if "필수 통합 failure journey" not in capstone or "사람 검토 질문" not in capstone:
        fail("capstone이 단계 반복과 사람 판단을 구분하지 않습니다.")

    print("MECHANICAL EXERCISE STRUCTURE OK stages=6 contracts=linked")
    print("EXERCISE LIMIT: app behavior, device evidence, capstone synthesis, and stable status need separate gates/review")


if __name__ == "__main__":
    main()
