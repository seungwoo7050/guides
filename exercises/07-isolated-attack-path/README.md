# 실습 07 — 격리된 공격 경로·패치·탐지

이 실습은 `LedgerLab`의 합성 상태를 사용해 **권한이 넓어지는 사건을 재현하고, 원인을 수정한 뒤 같은 시도가 차단·탐지되는지** 확인합니다. 외부 네트워크, 실제 credential, 관리자 권한과 container가 필요하지 않습니다.

여기서 권한 상승은 다른 사용자의 report를 읽는 수평 권한 상승이고, 내부 이동은 한 job의 worker credential이 다른 job object에 접근하는 capability 확장입니다. OS `root` 획득이나 exploit payload는 범위 밖입니다.

## 시작 상태와 미완성 부분

[`skeleton/ledgerlab_policy.py`](skeleton/ledgerlab_policy.py)는 실행 가능하지만 의도적으로 다음 계약이 빠져 있습니다.

- report owner·tenant를 같은 authorization decision에서 확인하지 않습니다.
- worker credential의 job·object prefix·expiry·revocation을 모두 강제하지 않습니다.
- deny event와 detector가 동일 공격 경로를 재구성하지 못합니다.

취약 상태를 먼저 재현합니다.

```sh
python3 exercises/07-isolated-attack-path/tests/check.py \
  --implementation exercises/07-isolated-attack-path/skeleton/ledgerlab_policy.py \
  --expect vulnerable
```

학습자 work를 안전하게 만듭니다.

```sh
python3 scripts/new_workspace.py exercise 07-isolated-attack-path
```

기존 `work/`가 있거나 symlink이면 도구는 덮어쓰지 않고 실패합니다.

## 공개 행동 계약

구현은 다음 함수를 제공합니다.

```python
authorize_report(state, request) -> {"decision": "allow|deny", "reason": str, "event": dict}
authorize_object(state, request) -> {"decision": "allow|deny", "reason": str, "event": dict}
detect(events) -> list[dict]
```

구현 모양은 자유롭지만 다음 상태를 보존해야 합니다.

- owner의 completed report read와 현재 job credential의 object read는 허용됩니다.
- foreign owner·tenant, unknown resource, 누락 context, expired·revoked credential, cross-job과 prefix 혼동은 거절됩니다.
- policy context를 확인할 수 없으면 fail closed합니다.
- authorization 판정은 report/object state를 바꾸지 않습니다.
- 모든 판정은 actor·effective actor·credential·tenant·job·action·resource·decision·reason·correlation·policy version을 조사 가능한 event로 남깁니다.
- 같은 cross-scope 시도는 detector의 positive fixture가 되고 정상 owner/job 흐름은 alert를 만들지 않습니다.
- duplicate·out-of-order event가 alert 수를 부풀리거나 evidence 연결을 깨뜨리지 않습니다.

## 정상·경계·대표 실패

| 종류 | 사례 | 관찰할 결과 |
|---|---|---|
| 정상 | owner가 자신의 completed report를 읽음 | allow, 상태 불변, 완전한 audit event |
| 정상 | job-81 credential이 job-81 prefix를 읽음 | allow |
| 경계 | `job-9`와 `job-9x`, expiry 직전·직후 | path segment와 시간 경계에 맞는 결정 |
| 실패 | user-b가 user-a report를 요청 | deny, resource 내용·상태 비노출 |
| 실패 | job-81 credential이 job-9 object를 요청 | deny와 cross-scope event |
| 실패 | policy unavailable, revoked credential | fail closed |
| 탐지 | 동일 cross-scope deny sequence | 하나의 alert와 원본 event ID |
| 비탐지 | 정상 access와 duplicate delivery | alert 없음 |

## 작업

1. 취약 skeleton에서 두 공격 전제와 상태 oracle을 기록합니다.
2. root cause를 설명하고 최소 change set으로 authorization과 event 계약을 복원합니다.
3. completion 검사를 실행합니다.
4. skeleton과 work의 diff, 검사 출력과 behavior evidence를 보존합니다.
5. 검사 범위와 production에 일반화할 수 없는 부분을 기록합니다.

```sh
python3 exercises/07-isolated-attack-path/tests/check.py \
  --implementation exercises/07-isolated-attack-path/work/ledgerlab_policy.py \
  --expect secure \
  --evidence exercises/07-isolated-attack-path/work/behavior-evidence.json
```

## 제출 증거와 사람 검토

- 취약 상태 재현 출력과 pre/post state hash
- `skeleton` 대비 patch diff와 root-cause 설명
- 정상·경계·failure·known-bad 검사 출력
- deny event, detector positive·negative 결과
- `behavior-evidence.json`
- cleanup 결과와 검증 한계

리뷰어는 다음을 판단합니다.

1. patch가 단순 deny-all이 아니라 정상 기능을 보존합니까?
2. route 하나의 증상만 막지 않고 owner/job scope의 정본에서 불변식을 강제합니까?
3. prefix·expiry·revocation·누락 context 우회가 남아 있습니까?
4. detector가 같은 공격을 가리키며 benign·duplicate·out-of-order를 과잉 탐지하지 않습니까?
5. 합성 모델이 실제 cloud IAM, OS isolation, production telemetry를 증명하지 못한다는 한계를 밝혔습니까?

기준 구현은 한 가지 공개 계약 충족 예시일 뿐 유일한 설계 정답이 아닙니다.
