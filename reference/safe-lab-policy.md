# 안전한 보안 실습 정책

이 정책은 저장소가 제공하는 모든 보안 실습과 후속 구현 profile에 적용됩니다. 목적은 기술적 위험뿐 아니라 허가·제3자·데이터·복구 경계를 먼저 고정하는 것입니다.

## 1. 허가 없이는 시작하지 않습니다

허가는 대상 소유자 또는 합법적으로 권한을 위임할 수 있는 주체가 제공합니다. 다음 항목이 문서로 확인되지 않으면 평가를 시작하지 않습니다.

- 대상 asset과 environment
- 허가된 identity와 계정
- 시작·종료 시각
- 허용 행동과 금지 행동
- 요청·자원·데이터 예산
- stop condition과 긴급 연락
- 증거 보존·공유·삭제 규칙
- 제3자 asset 처리

오픈된 포트, 공개 URL, 테스트 계정 또는 bug bounty의 존재만으로 모든 행동이 허가되는 것은 아닙니다.

## 2. 기본 실습 경계

이 저장소의 기본 profile은 다음만 사용합니다.

```text
저장소 내부 fixture
+ 합성 계정과 합성 데이터
+ 임시 작업 디렉터리
+ loopback
+ 필요할 때 격리된 로컬 process/container
```

루트 검증은 외부 네트워크, 관리자 권한과 실제 credential을 요구하지 않습니다.

## 3. 금지 행동

- 허가받지 않은 외부 host·domain·IP·service 평가
- 계정 추측, password spraying, credential stuffing
- phishing, social engineering과 제3자 접촉
- 실제 malware, persistence, evasion과 command-and-control
- production data·개인정보·실제 secret 획득 또는 반출
- 의도적인 service degradation, resource exhaustion과 대량 요청
- host mount, privileged container와 production cloud credential 사용
- 공급자·CDN·registry 등 scope 밖 제3자 우회 평가
- 영향 판정에 필요하지 않은 추가 권한·데이터 획득

## 4. 최소 영향 원칙

취약점 증명은 다음 순서로 진행하며 충분한 증거가 생기면 중단합니다.

```text
정적·문서 근거
→ 합성 fixture
→ 최소 runtime 관찰
→ synthetic flag 또는 상태 oracle
→ 중단과 cleanup
```

실제 데이터 한 건을 읽는 대신 자신이 만든 합성 object에 대한 authorization oracle을 사용합니다. write·delete 영향은 disposable resource에서만 확인하고, 복구 가능성을 먼저 검증합니다.

## 5. 중단 조건

최소한 다음 상황에서 즉시 중단합니다.

- scope 밖 asset 또는 실제 사용자 데이터가 나타남
- 예상하지 못한 외부 egress 또는 제3자 호출이 발생함
- production identity·credential이 노출됨
- 서비스 안정성이나 다른 사용자의 작업에 영향이 생김
- log·artifact가 허가된 저장 위치를 벗어남
- 평가 환경과 운영 환경의 분리가 불확실해짐
- 담당자와 연락할 수 없거나 허가 해석이 달라짐
- 자동화가 지정한 request·time·cost budget을 초과함

중단 뒤에는 증거를 지우기 전에 담당자와 보존 범위를 확인합니다.

## 6. 합성 데이터와 credential

- 실제 형식과 구분되는 명시적 prefix를 사용합니다.
- 권한은 실습 resource에만 제한합니다.
- 짧은 expiry와 독립된 identity를 사용합니다.
- source, log, screenshot과 report에 secret value를 넣지 않습니다.
- 종료 뒤 credential을 폐기하고 resource가 남지 않았는지 확인합니다.

예:

```text
user: lab-user-17
object: synthetic/tenant-17/report-a
credential id: lab-cred-20260809-01
secret value: 저장하거나 보고하지 않음
```

## 7. 증거 처리

증거에는 최소한 다음 metadata를 남깁니다.

- 수집 시각과 time source
- 대상 환경과 asset ID
- 수집 identity
- 수집 방법과 변경 여부
- 원본 위치와 hash 또는 immutable ID
- 접근할 수 있는 사람
- 보존 기간과 삭제 조건

필요한 field만 보존하고 token, 개인정보와 민감 payload는 redact합니다. redact 전 원본이 필요하다면 승인된 별도 저장소와 접근 기록을 사용합니다.

## 8. 자동화와 에이전트

자동화된 평가 도구와 AI agent에는 사람보다 더 좁은 실행 경계를 적용합니다.

- allowlisted tool과 target만 제공합니다.
- 직접 shell·network·credential 접근을 기본 허용하지 않습니다.
- request·process·time·cost·output budget을 강제합니다.
- 모든 tool call과 정책 거부를 외부에서 기록합니다.
- 고위험 write·delete·identity 변경은 사람 승인을 요구합니다.
- 성공 판정은 agent 설명이 아니라 외부 verifier가 수행합니다.
- 취소 뒤 child process·workspace·credential이 정리되는지 검사합니다.

AI 전용 공격과 방어는 이 브랜치의 범위 밖이지만, 일반 평가에서도 자동화가 권한을 확대하지 않도록 이 원칙을 사용합니다.

## 9. 종료와 cleanup

실습 종료 조건은 “도구가 끝남”이 아닙니다.

- 임시 process와 container 종료
- network·volume·workspace 제거
- 합성 identity와 credential 폐기
- 변경된 설정 복원
- 남은 artifact와 log 위치 기록
- 실패한 cleanup과 owner 기록
- 정상 기능과 보안 통제 재검증

cleanup 자체도 결과물의 일부입니다.
