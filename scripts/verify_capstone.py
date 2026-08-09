#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from capstone_behavior import BehaviorRunError, SKELETON, capture, capture_known_bad_quality, expected_patch


REQUIRED_MARKDOWN = {
    "scope.md": [
        ("평가 목적", "목적"), ("허가",), ("범위",), ("허용 행동",),
        ("금지 행동",), ("실행 예산", "예산"), ("중단 조건",),
        ("증거 처리",), ("정리", "cleanup"),
    ],
    "threat-model.md": [
        ("시스템 경계",), ("자산",), ("행위자",), ("신뢰 경계",),
        ("위협",), ("공격 경로",), ("choke point", "차단 지점"),
        ("가정", "미확인"),
    ],
    "security-requirements.md": [
        ("추적표",), ("요구사항",), ("enforcement", "강제"),
        ("runtime evidence", "운영 증거"), ("예외", "expiry"),
    ],
    "test-plan.md": [
        ("검증할 주장",), ("테스트 행렬",), ("oracle",),
        ("known-bad",), ("실행 근거",), ("한계",),
    ],
    "remediation-plan.md": [
        ("즉시 완화",), ("원인 수정",), ("유사 경로",),
        ("credential", "자격 증명"), ("회귀",),
        ("배포",), ("종료 조건",),
    ],
    "detection-plan.md": [
        ("event schema", "이벤트 스키마"), ("identity chain", "identity"),
        ("탐지 가설",), ("분석 규칙",), ("known-positive",),
        ("triage",), ("pipeline health",),
    ],
    "incident-timeline.md": [
        ("incident 범위", "사고 범위"), ("timeline",), ("증거 보존",),
        ("containment",), ("eradication",), ("recovery", "복구"),
        ("communication",), ("미확인",),
    ],
    "final-report.md": [
        ("executive summary", "요약"), ("검증된 상태",),
        ("공격 경로",), ("open finding", "미해결"),
        ("release 결정",), ("risk owner",),
        ("production validation",), ("evidence 한계", "근거 한계"),
        ("다음 프로젝트", "다음 단계"),
    ],
    "behavior-review.md": [
        ("end-to-end trace",), ("취약 상태",), ("causal root cause",),
        ("최소 patch",), ("known-bad",), ("corrected deny",),
        ("positive", "negative"), ("cleanup",), ("검증 한계",),
    ],
}

VALIDATION_STATUS = {"confirmed", "false-positive", "not-reproducible", "unknown"}
TREATMENTS = {"remediate", "mitigate", "accept", "defer", "not-applicable"}
LIFECYCLE_STATUS = {"open", "assigned", "in-progress", "ready-for-retest", "closed", "reopened"}
RATINGS = {"critical", "high", "medium", "low", "informational", "unrated"}
CONFIDENCE = {"high", "medium", "low"}
UNFILLED = re.compile(r"(?i)(?:\bTODO\b|\bTBD\b|\?\?\?|<\s*fill|작성\s*필요|미작성)")
ID_PATTERNS = {
    prefix: re.compile(rf"(?<![A-Z0-9-]){prefix}-[A-Z0-9][A-Z0-9-]*(?![A-Z0-9-])", re.I)
    for prefix in ("CAND", "THR", "REQ", "TEST", "FND", "PATCH", "DET")
}
DATE_LIKE = re.compile(r"(?<!\d)(20\d{2}-\d{2}-\d{2})(?!\d)")
TRACE_KEYS = {
    "threat_ids": "THR",
    "requirement_ids": "REQ",
    "test_ids": "TEST",
    "patch_ids": "PATCH",
    "detection_ids": "DET",
}
EXPECTED_BEHAVIOR_CHECKS = {
    "LAB-NORMAL-OWNER",
    "LAB-DENY-CROSS-OWNER",
    "LAB-DENY-PENDING",
    "LAB-DENY-UNKNOWN-REPORT",
    "LAB-DENY-FOREIGN-TENANT",
    "LAB-DENY-REPORT-STATE-TENANT",
    "LAB-DENY-DELEGATED-REPORT-ACTOR",
    "LAB-DENY-POLICY-UNAVAILABLE",
    "LAB-DENY-MISSING-REPORT-CONTEXT",
    "LAB-DENY-REPORT-ACTION",
    "LAB-NORMAL-JOB",
    "LAB-DENY-OBJECT-POLICY-UNAVAILABLE",
    "LAB-DENY-CREDENTIAL-STATE-TENANT",
    "LAB-DENY-DELEGATED-OBJECT-ACTOR",
    "LAB-DENY-CROSS-JOB",
    "LAB-DENY-PREFIX-CONFUSION",
    "LAB-DENY-EXPIRED",
    "LAB-DENY-REVOKED",
    "LAB-DENY-AT-EXPIRY",
    "LAB-DENY-CREDENTIAL-ACTOR",
    "LAB-DENY-MISSING-JOB-CONTEXT",
    "LAB-DETECT-BENIGN",
    "LAB-DETECT-POSITIVE",
    "LAB-DETECT-CORRELATION",
}


class CapstoneError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise CapstoneError(code, message)


def nonempty(value: object, label: str, minimum: int = 3, code: str = "E_FINDINGS_SCHEMA") -> str:
    if not isinstance(value, str) or len(value.strip()) < minimum or UNFILLED.search(value):
        fail(code, f"{label}: 구체적인 값을 작성해야 합니다.")
    return value.strip()


def string_list(value: object, label: str, minimum_items: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum_items:
        fail("E_FINDINGS_SCHEMA", f"{label}: {minimum_items}개 이상의 항목이 필요합니다.")
    return [nonempty(item, f"{label}[{index}]") for index, item in enumerate(value)]


def canonical_id(value: object, label: str, prefix: str) -> str:
    identifier = nonempty(value, label)
    if not re.fullmatch(rf"{prefix}-[A-Z0-9][A-Z0-9-]*", identifier, re.I):
        fail("E_FINDINGS_SCHEMA", f"{label}: {prefix}- 형식을 사용합니다.")
    return identifier.upper()


def canonical_id_list(value: object, label: str, prefix: str, minimum_items: int = 1) -> set[str]:
    if not isinstance(value, list) or len(value) < minimum_items:
        fail("E_FINDINGS_SCHEMA", f"{label}: {minimum_items}개 이상의 {prefix}- ID가 필요합니다.")
    result: set[str] = set()
    for index, item in enumerate(value):
        identifier = canonical_id(item, f"{label}[{index}]", prefix)
        if identifier in result:
            fail("E_DUPLICATE_ID", f"{label}: 대소문자를 무시하면 중복인 ID {identifier}")
        result.add(identifier)
    return result


def iso_date(value: object, label: str) -> date:
    raw = nonempty(value, label)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        fail("E_DATE", f"{label}: YYYY-MM-DD 형식이어야 합니다.")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        fail("E_DATE", f"{label}: 실제 존재하는 ISO 날짜여야 합니다: {raw}")


def headings(text: str) -> list[str]:
    return [match.group(1).strip().lower() for match in re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text)]


def regular_file(path: Path, label: str) -> None:
    if path.is_symlink():
        fail("E_FILE_SYMLINK", f"{label}: symlink 파일은 사용할 수 없습니다: {path}")
    if not path.is_file():
        fail("E_FILE_MISSING", f"필수 파일이 없습니다: {label}")


def require_sections(path: Path, alternatives: list[tuple[str, ...]]) -> str:
    regular_file(path, path.name)
    text = path.read_text(encoding="utf-8")
    if UNFILLED.search(text):
        fail("E_UNFILLED", f"{path.name}: TODO 또는 미작성 표시가 남아 있습니다.")
    section_headings = headings(text)
    if not section_headings:
        fail("E_SECTION", f"{path.name}: Markdown heading이 없습니다.")
    for group in alternatives:
        if not any(any(term.lower() in heading for term in group) for heading in section_headings):
            fail("E_SECTION", f"{path.name}: 필수 section이 없습니다: {' / '.join(group)}")
    body = re.sub(r"(?m)^#{1,6}\s+.*$", "", text)
    body = re.sub(r"[\s|`#>*_-]", "", body)
    if len(body) < 120:
        fail("E_CONTENT", f"{path.name}: heading 외의 판단 내용이 너무 적습니다.")
    return text


def load_json_object(path: Path, label: str) -> dict:
    regular_file(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail("E_JSON", f"{label}: JSON을 읽을 수 없습니다: {exc}")
    if not isinstance(value, dict):
        fail("E_JSON", f"{label}: 최상위 값은 object여야 합니다.")
    return value


def load_candidates(work: Path, explicit: Path | None) -> set[str]:
    candidate_path = explicit.resolve() if explicit else work.parent / "scenario/candidate-findings.json"
    data = load_json_object(candidate_path, "scenario candidate 파일")
    rows = data.get("candidates")
    if not isinstance(rows, list) or not rows:
        fail("E_CANDIDATES", "scenario candidate 목록이 비어 있습니다.")
    result: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            fail("E_CANDIDATES", f"candidates[{index}]: object여야 합니다.")
        candidate_id = canonical_id(row.get("id"), f"candidates[{index}].id", "CAND")
        if candidate_id in result:
            fail("E_DUPLICATE_ID", f"대소문자를 무시하면 중복인 candidate ID: {candidate_id}")
        result.add(candidate_id)
    return result


def validate_evidence(value: object, label: str) -> None:
    if not isinstance(value, list) or not value:
        fail("E_FINDINGS_SCHEMA", f"{label}: 최소 한 개의 evidence가 필요합니다.")
    evidence_ids: set[str] = set()
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, dict):
            fail("E_FINDINGS_SCHEMA", f"{item_label}: object여야 합니다.")
        evidence_id = nonempty(item.get("id"), f"{item_label}.id").upper()
        if evidence_id in evidence_ids:
            fail("E_DUPLICATE_ID", f"{label}: 대소문자를 무시하면 중복인 evidence ID {evidence_id}")
        evidence_ids.add(evidence_id)
        nonempty(item.get("source"), f"{item_label}.source")
        nonempty(item.get("observation"), f"{item_label}.observation", 12)
        nonempty(item.get("supports"), f"{item_label}.supports", 8)


def validate_treatment(row: dict, label: str, validation_status: str, treatment: str | None) -> None:
    if treatment is not None and treatment not in TREATMENTS:
        fail("E_FINDING_STATE", f"{label}.treatment: 허용 값은 {sorted(TREATMENTS)} 또는 null입니다.")
    if validation_status == "confirmed":
        if treatment is None or treatment == "not-applicable":
            fail("E_FINDING_STATE", f"{label}: confirmed finding에는 실제 treatment가 필요합니다.")
    elif validation_status == "false-positive":
        if treatment != "not-applicable":
            fail("E_FINDING_STATE", f"{label}: false-positive treatment는 not-applicable이어야 합니다.")
    else:
        if treatment not in {None, "defer"}:
            fail("E_FINDING_STATE", f"{label}: {validation_status} treatment는 null 또는 defer만 허용합니다.")

    if treatment == "defer":
        decision = row.get("defer_decision")
        if not isinstance(decision, dict):
            fail("E_FINDING_STATE", f"{label}.defer_decision: owner·review date·trigger가 필요합니다.")
        nonempty(decision.get("owner"), f"{label}.defer_decision.owner")
        iso_date(decision.get("review_date"), f"{label}.defer_decision.review_date")
        nonempty(decision.get("review_trigger"), f"{label}.defer_decision.review_trigger", 12)

    acceptance = row.get("risk_acceptance")
    if treatment == "accept":
        if validation_status != "confirmed":
            fail("E_FINDING_STATE", f"{label}: accept는 confirmed finding에만 허용됩니다.")
        if not isinstance(acceptance, dict):
            fail("E_FINDING_STATE", f"{label}.risk_acceptance: 승인 근거가 필요합니다.")
        nonempty(acceptance.get("authority"), f"{label}.risk_acceptance.authority")
        nonempty(acceptance.get("owner"), f"{label}.risk_acceptance.owner")
        iso_date(acceptance.get("expiry"), f"{label}.risk_acceptance.expiry")
        string_list(acceptance.get("compensating_controls"), f"{label}.risk_acceptance.compensating_controls")
        nonempty(acceptance.get("monitoring"), f"{label}.risk_acceptance.monitoring", 12)
        nonempty(acceptance.get("review_trigger"), f"{label}.risk_acceptance.review_trigger", 12)
    elif acceptance not in (None, {}):
        fail("E_FINDING_STATE", f"{label}.risk_acceptance: treatment가 accept일 때만 사용할 수 있습니다.")


def validate_findings(path: Path, candidate_ids: set[str]) -> dict[str, dict]:
    data = load_json_object(path, "findings.json")
    if data.get("schema_version") != 2:
        fail("E_FINDINGS_SCHEMA", "findings.json.schema_version은 2여야 합니다.")
    rows = data.get("findings")
    if not isinstance(rows, list) or not rows:
        fail("E_FINDINGS_SCHEMA", "findings.json.findings는 비어 있지 않은 배열이어야 합니다.")

    findings: dict[str, dict] = {}
    covered_candidates: set[str] = set()
    for index, row in enumerate(rows):
        label = f"findings[{index}]"
        if not isinstance(row, dict):
            fail("E_FINDINGS_SCHEMA", f"{label}: object여야 합니다.")
        finding_id = canonical_id(row.get("id"), f"{label}.id", "FND")
        if finding_id in findings:
            fail("E_DUPLICATE_ID", f"대소문자를 무시하면 중복인 finding ID: {finding_id}")
        candidate_id = canonical_id(row.get("candidate_id"), f"{label}.candidate_id", "CAND")
        if candidate_id in covered_candidates:
            fail("E_DUPLICATE_ID", f"대소문자를 무시하면 두 번 판정한 candidate: {candidate_id}")
        if candidate_id not in candidate_ids:
            fail("E_CANDIDATE_COVERAGE", f"scenario에 없는 candidate_id: {candidate_id}")
        covered_candidates.add(candidate_id)

        nonempty(row.get("title"), f"{label}.title", 12)
        validation_status = nonempty(row.get("validation_status"), f"{label}.validation_status")
        if validation_status not in VALIDATION_STATUS:
            fail("E_FINDING_STATE", f"{label}.validation_status: 허용 값은 {sorted(VALIDATION_STATUS)}입니다.")
        treatment_value = row.get("treatment")
        if treatment_value is not None and not isinstance(treatment_value, str):
            fail("E_FINDING_STATE", f"{label}.treatment: string 또는 null이어야 합니다.")
        treatment = treatment_value.strip() if isinstance(treatment_value, str) else None
        lifecycle_status = nonempty(row.get("lifecycle_status"), f"{label}.lifecycle_status")
        if lifecycle_status not in LIFECYCLE_STATUS:
            fail("E_FINDING_STATE", f"{label}.lifecycle_status: 허용 값은 {sorted(LIFECYCLE_STATUS)}입니다.")

        duplicate_raw = row.get("duplicate_of")
        duplicate_of = None if duplicate_raw is None else canonical_id(duplicate_raw, f"{label}.duplicate_of", "FND")
        nonempty(row.get("asset"), f"{label}.asset")
        string_list(row.get("preconditions"), f"{label}.preconditions")
        validate_evidence(row.get("evidence"), f"{label}.evidence")
        nonempty(row.get("impact"), f"{label}.impact", 12)
        string_list(row.get("limitations"), f"{label}.limitations")

        if validation_status == "confirmed":
            nonempty(row.get("causal_mechanism"), f"{label}.causal_mechanism", 12)
            nonempty(row.get("proof_oracle"), f"{label}.proof_oracle", 12)
            nonempty(row.get("remediation"), f"{label}.remediation", 12)
            nonempty(row.get("retest"), f"{label}.retest", 12)
        elif validation_status == "false-positive":
            nonempty(row.get("disproven_assumption"), f"{label}.disproven_assumption", 12)
            nonempty(row.get("counterevidence"), f"{label}.counterevidence", 12)
            nonempty(row.get("reopen_trigger"), f"{label}.reopen_trigger", 12)
        elif validation_status == "not-reproducible":
            nonempty(row.get("reproduction_gap"), f"{label}.reproduction_gap", 12)
            nonempty(row.get("next_safe_evidence"), f"{label}.next_safe_evidence", 12)
            nonempty(row.get("reopen_trigger"), f"{label}.reopen_trigger", 12)
        else:
            string_list(row.get("unknowns"), f"{label}.unknowns")
            nonempty(row.get("next_safe_evidence"), f"{label}.next_safe_evidence", 12)
            nonempty(row.get("reopen_trigger"), f"{label}.reopen_trigger", 12)

        validate_treatment(row, label, validation_status, treatment)
        severity = row.get("severity")
        if not isinstance(severity, dict):
            fail("E_FINDINGS_SCHEMA", f"{label}.severity: object여야 합니다.")
        rating = nonempty(severity.get("rating"), f"{label}.severity.rating")
        if rating not in RATINGS:
            fail("E_FINDINGS_SCHEMA", f"{label}.severity.rating: 허용 값은 {sorted(RATINGS)}입니다.")
        nonempty(severity.get("rationale"), f"{label}.severity.rationale", 12)
        confidence = nonempty(row.get("confidence"), f"{label}.confidence")
        if confidence not in CONFIDENCE:
            fail("E_FINDINGS_SCHEMA", f"{label}.confidence: 허용 값은 {sorted(CONFIDENCE)}입니다.")

        trace = row.get("trace")
        if not isinstance(trace, dict):
            fail("E_FINDINGS_SCHEMA", f"{label}.trace: object여야 합니다.")
        canonical_trace = {
            key: canonical_id_list(
                trace.get(key),
                f"{label}.trace.{key}",
                prefix,
                minimum_items=1 if validation_status == "confirmed" else 0,
            )
            for key, prefix in TRACE_KEYS.items()
        }
        findings[finding_id] = {
            "candidate_id": candidate_id,
            "validation_status": validation_status,
            "treatment": treatment,
            "duplicate_of": duplicate_of,
            "trace": canonical_trace,
        }

    missing = sorted(candidate_ids - covered_candidates)
    extra = sorted(covered_candidates - candidate_ids)
    if missing or extra:
        fail("E_CANDIDATE_COVERAGE", f"candidate completeness 불일치: missing={missing} extra={extra}")

    for finding_id, finding in findings.items():
        duplicate_of = finding["duplicate_of"]
        if duplicate_of is not None:
            if duplicate_of == finding_id:
                fail("E_FINDING_STATE", f"{finding_id}: 자기 자신을 duplicate_of로 참조할 수 없습니다.")
            if duplicate_of not in findings:
                fail("E_FINDING_STATE", f"{finding_id}: 존재하지 않는 duplicate_of {duplicate_of}")
            seen = {finding_id}
            current = duplicate_of
            while current is not None:
                if current in seen:
                    fail("E_FINDING_STATE", f"duplicate_of 순환 참조: {finding_id}")
                seen.add(current)
                current = findings[current]["duplicate_of"]
    return findings


def ids(text: str, prefix: str) -> set[str]:
    return {identifier.upper() for identifier in ID_PATTERNS[prefix].findall(text)}


def all_dates_are_valid(text: str, label: str) -> None:
    matches = DATE_LIKE.findall(text)
    if not matches:
        fail("E_DATE", f"{label}: risk expiry 또는 재검토 날짜가 필요합니다.")
    for raw in matches:
        try:
            date.fromisoformat(raw)
        except ValueError:
            fail("E_DATE", f"{label}: 실제 존재하는 ISO 날짜여야 합니다: {raw}")


def require_trace(texts: dict[str, str], findings: dict[str, dict]) -> None:
    def require_known(text_name: str, prefix: str, known: set[str]) -> None:
        unknown = ids(texts[text_name], prefix) - known
        if unknown:
            fail("E_TRACE", f"{text_name}: 정의되지 않은 {prefix} ID {sorted(unknown)}")

    threat_ids = ids(texts["threat-model.md"], "THR")
    if len(threat_ids) < 3:
        fail("E_TRACE", "threat-model.md: 서로 다른 THR ID가 세 개 이상 필요합니다.")

    requirement_ids = ids(texts["security-requirements.md"], "REQ")
    if len(requirement_ids) < 3:
        fail("E_TRACE", "security-requirements.md: 서로 다른 REQ ID가 세 개 이상 필요합니다.")
    linked_threats = ids(texts["security-requirements.md"], "THR")
    if not linked_threats or not linked_threats.issubset(threat_ids):
        fail("E_TRACE", "security-requirements.md: threat-model에 존재하는 THR ID만 추적해야 합니다.")

    test_ids = ids(texts["test-plan.md"], "TEST")
    tested_requirements = ids(texts["test-plan.md"], "REQ")
    if len(test_ids) < 3 or len(tested_requirements) < 3 or not tested_requirements.issubset(requirement_ids):
        fail("E_TRACE", "test-plan.md: 존재하는 REQ ID 세 개 이상과 서로 다른 TEST ID 세 개 이상이 필요합니다.")

    finding_ids = set(findings)
    require_known("security-requirements.md", "FND", finding_ids)
    patch_ids = ids(texts["remediation-plan.md"], "PATCH")
    remediation_findings = ids(texts["remediation-plan.md"], "FND")
    if not patch_ids or not remediation_findings or not remediation_findings.issubset(finding_ids):
        fail("E_TRACE", "remediation-plan.md: 존재하는 FND ID와 PATCH ID를 참조해야 합니다.")

    detection_ids = ids(texts["detection-plan.md"], "DET")
    if len(detection_ids) < 2:
        fail("E_TRACE", "detection-plan.md: 서로 다른 DET ID가 두 개 이상 필요합니다.")
    if not ids(texts["detection-plan.md"], "FND").issubset(finding_ids):
        fail("E_TRACE", "detection-plan.md: 존재하는 FND ID만 참조해야 합니다.")

    require_known("incident-timeline.md", "FND", finding_ids)
    require_known("incident-timeline.md", "PATCH", patch_ids)
    require_known("incident-timeline.md", "DET", detection_ids)

    timeline_types = {
        value.upper()
        for value in re.findall(r"\b(?:FACT|HYPOTHESIS|DECISION|ACTION|RESULT|UNKNOWN)\b", texts["incident-timeline.md"], re.I)
    }
    if len(timeline_types) < 4:
        fail("E_TRACE", "incident-timeline.md: FACT·HYPOTHESIS·DECISION·ACTION·RESULT·UNKNOWN 중 네 종류 이상이 필요합니다.")

    final = texts["final-report.md"]
    if not re.search(r"(?im)^\s*(?:decision|release\s*결정)\s*[:：-]\s*(go|conditional-go|no-go)\s*$", final):
        fail("E_TRACE", "final-report.md: `Release 결정: go|conditional-go|no-go`를 명시합니다.")
    all_dates_are_valid(final, "final-report.md")

    known_by_prefix = {
        "FND": finding_ids,
        "THR": threat_ids,
        "REQ": requirement_ids,
        "TEST": test_ids,
        "PATCH": patch_ids,
        "DET": detection_ids,
    }
    for text_name in ("behavior-review.md", "final-report.md"):
        for prefix, known in known_by_prefix.items():
            require_known(text_name, prefix, known)

    document_sets = {
        "THR": threat_ids,
        "REQ": requirement_ids,
        "TEST": test_ids,
        "PATCH": patch_ids,
        "DET": detection_ids,
    }
    for finding_id, finding in findings.items():
        for key, prefix in TRACE_KEYS.items():
            unknown = finding["trace"][key] - document_sets[prefix]
            if unknown:
                fail("E_TRACE", f"{finding_id}.trace.{key}: 문서에 없는 ID {sorted(unknown)}")

    coherent: list[str] = []
    for finding_id, finding in findings.items():
        if finding["validation_status"] != "confirmed":
            continue
        trace = finding["trace"]
        security_text = texts["security-requirements.md"]
        test_text = texts["test-plan.md"]
        remediation_text = texts["remediation-plan.md"]
        detection_text = texts["detection-plan.md"]
        incident_text = texts["incident-timeline.md"]
        behavior_text = texts["behavior-review.md"]
        final_text = texts["final-report.md"]
        checks = [
            finding_id in ids(security_text, "FND"),
            trace["threat_ids"].issubset(ids(security_text, "THR")),
            trace["requirement_ids"].issubset(ids(security_text, "REQ")),
            trace["requirement_ids"].issubset(ids(test_text, "REQ")),
            trace["test_ids"].issubset(ids(test_text, "TEST")),
            finding_id in ids(remediation_text, "FND"),
            trace["patch_ids"].issubset(ids(remediation_text, "PATCH")),
            finding_id in ids(detection_text, "FND"),
            trace["patch_ids"].issubset(ids(detection_text, "PATCH")),
            trace["detection_ids"].issubset(ids(detection_text, "DET")),
            finding_id in ids(incident_text, "FND"),
            trace["patch_ids"].issubset(ids(incident_text, "PATCH")),
            trace["detection_ids"].issubset(ids(incident_text, "DET")),
            finding_id in ids(behavior_text, "FND"),
            all(trace[key].issubset(ids(behavior_text, prefix)) for key, prefix in TRACE_KEYS.items()),
            finding_id in ids(final_text, "FND"),
            all(trace[key].issubset(ids(final_text, prefix)) for key, prefix in TRACE_KEYS.items()),
        ]
        if all(checks):
            coherent.append(finding_id)
    if not coherent:
        fail("E_TRACE", "confirmed finding 하나 이상을 FND→THR→REQ→TEST→PATCH→DET→incident/recovery→release로 연결해야 합니다.")


def validate_behavior_evidence(value: dict, expected_profile: str, label: str) -> None:
    if value.get("schema_version") != 1 or value.get("profile") != expected_profile:
        fail("E_BEHAVIOR_EVIDENCE", f"{label}: schema_version=1과 profile={expected_profile}이 필요합니다.")
    before = nonempty(value.get("state_before_sha256"), f"{label}.state_before_sha256", 64, "E_BEHAVIOR_EVIDENCE")
    after = nonempty(value.get("state_after_sha256"), f"{label}.state_after_sha256", 64, "E_BEHAVIOR_EVIDENCE")
    if before != after:
        fail("E_BEHAVIOR_EVIDENCE", f"{label}: authorization 검사가 보호 상태를 변경했습니다.")
    checks = value.get("checks")
    if not isinstance(checks, list) or not checks:
        fail("E_BEHAVIOR_EVIDENCE", f"{label}.checks: 비어 있지 않은 배열이어야 합니다.")
    check_ids: set[str] = set()
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            fail("E_BEHAVIOR_EVIDENCE", f"{label}.checks[{index}]: object여야 합니다.")
        check_id = nonempty(check.get("id"), f"{label}.checks[{index}].id", code="E_BEHAVIOR_EVIDENCE")
        if check_id in check_ids:
            fail("E_BEHAVIOR_EVIDENCE", f"{label}: 중복 check ID {check_id}")
        check_ids.add(check_id)
        if check.get("passed") is not True:
            fail("E_BEHAVIOR_EVIDENCE", f"{label}: 실패한 check {check_id}")
    if expected_profile == "secure" and not EXPECTED_BEHAVIOR_CHECKS.issubset(check_ids):
        fail("E_BEHAVIOR_EVIDENCE", f"{label}: 필수 정상·경계·실패·탐지 check가 없습니다: {sorted(EXPECTED_BEHAVIOR_CHECKS - check_ids)}")


def validate_behavior(work: Path) -> None:
    if (work / "behavior-lab").is_symlink():
        fail("E_FILE_SYMLINK", "behavior-lab 디렉터리는 symlink일 수 없습니다.")
    implementation = work / "behavior-lab/ledgerlab_policy.py"
    regular_file(implementation, "behavior-lab/ledgerlab_policy.py")
    vulnerable_path = work / "vulnerable-evidence.json"
    secure_path = work / "behavior-evidence.json"
    known_bad_path = work / "known-bad-evidence.json"
    patch_path = work / "behavior-patch.diff"
    vulnerable_submitted = load_json_object(vulnerable_path, "vulnerable-evidence.json")
    secure_submitted = load_json_object(secure_path, "behavior-evidence.json")
    known_bad_submitted = load_json_object(known_bad_path, "known-bad-evidence.json")
    regular_file(patch_path, "behavior-patch.diff")

    validate_behavior_evidence(vulnerable_submitted, "vulnerable", "vulnerable-evidence.json")
    validate_behavior_evidence(secure_submitted, "secure", "behavior-evidence.json")
    try:
        vulnerable_actual, _ = capture(SKELETON, "vulnerable")
        secure_actual, output = capture(implementation, "secure")
        known_bad_actual = capture_known_bad_quality()
    except BehaviorRunError as exc:
        detail = exc.output.strip().splitlines()[-1] if exc.output.strip() else str(exc)
        fail("E_BEHAVIOR_RUN", f"learner implementation 재실행 실패: {detail}")
    if vulnerable_submitted != vulnerable_actual:
        fail("E_BEHAVIOR_EVIDENCE", "vulnerable-evidence.json이 canonical skeleton 재실행 결과와 다릅니다.")
    if secure_submitted != secure_actual:
        fail("E_BEHAVIOR_EVIDENCE", "behavior-evidence.json이 learner implementation 재실행 결과와 다릅니다.")
    if known_bad_submitted != known_bad_actual:
        fail("E_BEHAVIOR_EVIDENCE", "known-bad-evidence.json이 canonical mutant meta-test 재실행 결과와 다릅니다.")

    expected = expected_patch(implementation)
    if not expected:
        fail("E_BEHAVIOR_PATCH", "behavior implementation이 취약 skeleton과 같습니다.")
    if patch_path.read_text(encoding="utf-8") != expected:
        fail("E_BEHAVIOR_PATCH", "behavior-patch.diff가 현재 implementation의 exact diff와 다릅니다.")
    if "LAB RESULT PASS" not in output:
        fail("E_BEHAVIOR_RUN", "learner implementation의 completion oracle을 확인할 수 없습니다.")


def main() -> int:
    parser = argparse.ArgumentParser(description="LedgerLab Capstone의 구조·trace·격리 행동 evidence를 검사합니다.")
    parser.add_argument("workdir", type=Path)
    parser.add_argument("--scenario-candidates", type=Path)
    args = parser.parse_args()

    unresolved_work = args.workdir.absolute()
    if unresolved_work.is_symlink():
        fail("E_FILE_SYMLINK", f"작업 디렉터리가 symlink입니다: {unresolved_work}")
    work = unresolved_work.resolve()
    if not work.is_dir():
        fail("E_WORKDIR", f"작업 디렉터리가 없습니다: {work}")

    texts: dict[str, str] = {}
    for filename, sections in REQUIRED_MARKDOWN.items():
        texts[filename] = require_sections(work / filename, sections)
    candidate_ids = load_candidates(work, args.scenario_candidates)
    findings = validate_findings(work / "findings.json", candidate_ids)
    require_trace(texts, findings)
    validate_behavior(work)

    print(
        "CAPSTONE OK "
        f"markdown={len(REQUIRED_MARKDOWN)} findings={len(findings)} "
        f"candidates={len(candidate_ids)} behavior=reexecuted"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CapstoneError as exc:
        print(f"CAPSTONE ERROR [{exc.code}]: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(f"CAPSTONE ERROR [E_IO]: {exc}", file=sys.stderr)
        raise SystemExit(1)
