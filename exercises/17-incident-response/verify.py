#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().upper() != "TODO"


def mapping(value: Any, label: str, errors: list[str]) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{label}는 매핑이어야 합니다.")
        return {}
    return value


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "reference"}:
        print("사용법: verify.py [skeleton|reference]", file=sys.stderr)
        return 2
    response = yaml.safe_load((ROOT / sys.argv[1] / "response.yaml").read_text(encoding="utf-8"))
    fixture = yaml.safe_load((ROOT / "fixtures" / "incident.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    fixture_observation_times = {
        str(event.get("at"))
        for event in fixture.get("events", [])
        if isinstance(event, dict) and event.get("type") == "observation"
    }
    root = mapping(response, "response", errors)
    if root.get("schema_version") != 1 or root.get("incident_id") != fixture.get("incident_id"):
        errors.append("schema_version 또는 incident_id가 입력과 다릅니다.")
    if root.get("severity") not in {"SEV-1", "SEV-2", "SEV-3", "SEV-4"}:
        errors.append("severity가 필요합니다.")
    if not nonempty(root.get("user_impact")):
        errors.append("사용자 기능과 시작 시각을 포함한 user_impact가 필요합니다.")

    roles = mapping(root.get("roles"), "roles", errors)
    for role in ("incident_commander", "operations", "communications", "scribe"):
        if not nonempty(roles.get(role)):
            errors.append(f"roles.{role}가 필요합니다.")
    if root.get("change_freeze") is not True:
        errors.append("사고 중 production change freeze가 필요합니다.")

    observations = root.get("observations")
    if not isinstance(observations, list) or len(observations) < 4:
        errors.append("증거가 있는 observation을 네 개 이상 작성해야 합니다.")
        observations = []
    times: list[datetime] = []
    observation_ids: set[str] = set()
    for index, item in enumerate(observations):
        observation = mapping(item, f"observations[{index}]", errors)
        for key in ("id", "at", "evidence", "fact"):
            if not nonempty(observation.get(key)):
                errors.append(f"observations[{index}].{key}가 필요합니다.")
        if isinstance(observation.get("id"), str):
            observation_ids.add(observation["id"])
        at = str(observation.get("at"))
        try:
            times.append(datetime.fromisoformat(at.replace("Z", "+00:00")))
        except ValueError:
            errors.append(f"observation 시각 형식이 잘못됐습니다: {observation.get('at')}")
        if at not in fixture_observation_times:
            errors.append(
                f"observation은 입력 timeline의 관측 event 시각을 참조해야 합니다: {at}"
            )
    if times != sorted(times):
        errors.append("observation timeline이 시간순이 아닙니다.")

    hypotheses = root.get("hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) < 2:
        errors.append("대안 hypothesis를 두 개 이상 작성해야 합니다.")
        hypotheses = []
    for index, item in enumerate(hypotheses):
        hypothesis = mapping(item, f"hypotheses[{index}]", errors)
        for key in ("id", "statement", "test", "status"):
            if not nonempty(hypothesis.get(key)):
                errors.append(f"hypotheses[{index}].{key}가 필요합니다.")
        if hypothesis.get("status") not in {"leading", "unconfirmed", "confirmed", "rejected"}:
            errors.append(f"hypotheses[{index}].status가 올바르지 않습니다.")
        supporting = hypothesis.get("supporting_evidence")
        if not isinstance(supporting, list) or not supporting:
            errors.append(f"hypotheses[{index}]에 supporting_evidence가 필요합니다.")
        elif not all(isinstance(item, str) and item in observation_ids for item in supporting):
            errors.append(f"hypotheses[{index}]가 존재하지 않는 observation을 참조합니다.")
        contradicting = hypothesis.get("contradicting_evidence")
        if not isinstance(contradicting, list) or not all(nonempty(item) for item in contradicting):
            errors.append(f"hypotheses[{index}].contradicting_evidence는 문자열 목록이어야 합니다.")

    actions = root.get("initial_actions")
    if not isinstance(actions, list) or len(actions) < 3:
        errors.append("세 개 이상의 초기 조치가 필요합니다.")
        actions = []
    orders = []
    action_text = " ".join(str(item.get("action", "")) for item in actions if isinstance(item, dict)).lower()
    for index, item in enumerate(actions):
        action = mapping(item, f"initial_actions[{index}]", errors)
        if not isinstance(action.get("order"), int):
            errors.append(f"initial_actions[{index}].order가 정수여야 합니다.")
        else:
            orders.append(action["order"])
        for key in ("action", "reason", "owner"):
            if not nonempty(action.get(key)):
                errors.append(f"initial_actions[{index}].{key}가 필요합니다.")
        if action.get("reversible") is not True:
            errors.append(f"초기 조치는 가역적이어야 합니다: {action.get('action')}")
    if orders != list(range(1, len(actions) + 1)):
        errors.append("initial action order는 1부터 연속인 고유한 오름차순이어야 합니다.")
    if "보존" not in action_text and "preserve" not in action_text:
        errors.append("초기 조치에 증거 보존이 필요합니다.")
    if "배포" not in action_text and "change" not in action_text:
        errors.append("초기 조치에 변경 동결이 필요합니다.")

    rejected = root.get("rejected_actions")
    if not isinstance(rejected, list) or len(rejected) < 2:
        errors.append("위험한 제안을 두 개 이상 명시적으로 거부해야 합니다.")
        rejected = []
    rejected_text = " ".join(str(item.get("action", "")) for item in rejected if isinstance(item, dict)).lower()
    if "prune" not in rejected_text or "restart" not in rejected_text:
        errors.append("prune과 전체 restart 제안을 모두 검토·거부해야 합니다.")
    for index, item in enumerate(rejected):
        rejected_item = mapping(item, f"rejected_actions[{index}]", errors)
        if not nonempty(rejected_item.get("reason")):
            errors.append(f"rejected_actions[{index}].reason이 필요합니다.")

    mitigation = mapping(root.get("mitigation"), "mitigation", errors)
    for key in ("action", "success_condition", "rollback_or_stop_condition", "owner"):
        if not nonempty(mitigation.get(key)):
            errors.append(f"mitigation.{key}가 필요합니다.")

    verification = root.get("recovery_verification")
    if not isinstance(verification, list) or len(verification) < 5:
        errors.append("외부 기능·자원·데이터를 포함한 recovery verification이 필요합니다.")
        verification = []
    verification_text = " ".join(str(item) for item in verification).lower()
    for keyword in ("외부", "쓰기", "데이터"):
        if keyword not in verification_text:
            errors.append(f"recovery verification에 {keyword} 검사가 필요합니다.")

    communication = mapping(root.get("communication"), "communication", errors)
    for key in ("first_message", "next_update_at", "owner"):
        if not nonempty(communication.get(key)):
            errors.append(f"communication.{key}가 필요합니다.")
    if communication.get("root_cause_claimed") is not False:
        errors.append("초기 communication에서 확인되지 않은 root cause를 단정하면 안 됩니다.")
    try:
        next_update = datetime.fromisoformat(
            str(communication.get("next_update_at")).replace("Z", "+00:00")
        )
        if times and next_update <= max(times):
            errors.append("다음 communication 시각은 마지막 관측 뒤여야 합니다.")
    except ValueError:
        errors.append("communication.next_update_at 시각 형식이 잘못됐습니다.")

    followups = root.get("followups")
    if not isinstance(followups, list) or len(followups) < 3:
        errors.append("세 개 이상의 구체적인 followup이 필요합니다.")
        followups = []
    for index, item in enumerate(followups):
        followup = mapping(item, f"followups[{index}]", errors)
        for key in ("id", "owner", "deadline", "action", "verification"):
            if not nonempty(followup.get(key)):
                errors.append(f"followups[{index}].{key}가 필요합니다.")
        try:
            if date.fromisoformat(str(followup.get("deadline"))) < date(2026, 8, 7):
                errors.append(f"followup deadline이 사고일 이전입니다: {followup.get('id')}")
        except ValueError:
            errors.append(f"followup deadline 형식이 잘못됐습니다: {followup.get('id')}")

    text = (ROOT / sys.argv[1] / "response.yaml").read_text(encoding="utf-8").lower()
    for forbidden in ("password=", "authorization: bearer", "secret-value"):
        if forbidden in text:
            errors.append("사고 기록에 secret 원문이 포함되었습니다.")

    if errors:
        print(f"사고 대응 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: severity, roles, observations, hypotheses, safe actions, recovery와 followups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
