# 사고 대응과 runbook

장애 중에는 정보가 불완전하고 시간이 부족합니다. 평상시에는 합리적으로 보이는 명령도 압박 속에서 순서가 바뀌면 증거를 지우거나 피해를 키울 수 있습니다. 사고 대응의 목표는 모든 원인을 즉시 설명하는 것이 아니라 다음 순서를 지키는 것입니다.

```text
사용자 영향 확인
→ 지휘와 의사소통 경로 설정
→ 변경 동결과 증거 보존
→ 안전한 완화
→ 복구 검증
→ 원인 분석
→ 재발 방지와 운영 계약 수정
```

대응 실습은 [`exercises/17-incident-response`](../exercises/17-incident-response/)입니다.

## 1. 장애, 사건과 보안 사고

용어를 미리 정합니다.

- 장애: 기대한 서비스 수준을 만족하지 못하는 상태
- 사건: 운영자가 조사·조치해야 하는 비정상 event
- 보안 사고: 기밀성·무결성·가용성 또는 권한 경계가 침해됐거나 그 가능성이 높은 사건

단순 5xx 증가도 원인에 따라 배포 오류, DB 고갈 또는 credential 탈취일 수 있습니다. 초기에는 확정하지 않고 관찰 사실과 가설을 구분합니다.

## 2. 심각도

예시:

| 수준 | 사용자 영향 | 대응 |
|---|---|---|
| SEV-1 | 전체 핵심 기능 중단, 데이터 손실·보안 침해 가능 | 즉시 지휘·연락·완화 |
| SEV-2 | 주요 기능 또는 다수 사용자 영향 | 즉시 조사, 정해진 시간 안 완화 |
| SEV-3 | 제한된 기능·사용자, workaround 존재 | 근무 시간 내 처리 |
| SEV-4 | 사용자 영향 없음, 운영 위험·예방 작업 | ticket와 계획 |

심각도는 내부 원인의 흥미로움이 아니라 사용자·데이터 영향으로 정합니다. 새 증거가 생기면 올리거나 내릴 수 있습니다.

## 3. 역할

작은 팀에서는 한 사람이 여러 역할을 맡을 수 있지만 머릿속 책임을 구분합니다.

### Incident commander

- 우선순위와 심각도 결정
- 역할 할당
- 다음 update 시각 결정
- 위험한 변경 승인
- 종료 조건 판단

### Operations lead

- 진단과 완화 수행
- 실행 명령과 결과 기록
- production 변경 조정

### Communications lead

- 사용자·이해관계자 update
- 확인된 사실과 다음 update 시각 전달

### Scribe

- timeline
- 가설과 증거
- 의사결정과 승인
- 실행 결과

한 사람이 모두 수행하더라도 역할을 전환했음을 기록하면 분석과 의사결정이 섞이는 것을 줄입니다.

## 4. 첫 15분의 질문

시간은 예시이며 상황에 맞게 조정합니다.

```text
무슨 사용자 기능이 실패하는가?
언제 시작됐는가?
현재도 진행 중인가?
최근 배포·설정·DNS·secret 변경이 있었는가?
데이터 손실 또는 보안 침해 징후가 있는가?
영향을 줄이는 가장 안전한 가역 조치는 무엇인가?
누가 지휘하고 다음 update는 언제인가?
```

원인을 모른다는 이유로 update를 미루지 않습니다. 확인된 영향과 조사 중인 사실을 구분해 전달합니다.

## 5. 변경 동결

여러 사람이 동시에 임의 수정을 하면 인과관계를 잃습니다.

- 자동 배포 일시 중지
- 비필수 maintenance 중지
- production 변경은 incident commander를 통해 조정
- 한 번에 한 가설을 검증
- 변경 전후 시각과 결과 기록

사용자 영향을 줄이는 긴급 변경은 허용하되 기록합니다.

## 6. 증거 보존

가능한 경우 변경 전에 다음을 저장합니다.

```text
현재 release와 image digest
Compose config와 container 상태
최초 오류가 포함된 log 구간
host 시간과 timezone
자원 metric
DB 상태·schema version
DNS record와 제공 중인 인증서
최근 배포·secret 회전·backup 기록
```

민감한 값과 개인정보를 사고 채널에 무분별하게 붙이지 않습니다. 접근 통제된 위치에 보존하고 reference만 공유합니다.

container와 log를 정리하기 전에 원인 분석에 필요한 자료를 확보합니다. 그러나 증거 수집 때문에 복구가 지연되어 피해가 커지면 완화가 우선입니다.

## 7. 가설과 사실 분리

timeline에 다음 표시를 사용합니다.

```text
OBSERVATION  외부 probe에서 12:03부터 502 증가
CHANGE       11:58 release 2026-08-07.1 배포
HYPOTHESIS   새 app이 FPM worker를 고갈시킴
TEST         이전 release로 isolated smoke 실행
RESULT       이전 release도 같은 DB timeout 발생
DECISION     DB connection 고갈 완화 진행
```

최근 배포가 있었다는 사실만으로 원인이라고 단정하지 않습니다.

## 8. 완화, 복구와 근본 수정

### 완화

사용자 영향을 빠르게 줄이는 임시 조치입니다.

- 문제 release rollback
- 쓰기 기능 일시 중지
- traffic 또는 concurrency 제한
- 실패한 dependency 우회
- read-only mode
- disk emergency cleanup

### 복구

서비스를 운영 계약의 허용 상태로 되돌립니다.

- exact release 재배포
- DB connection 정상화
- backup 복원
- 인증서 교체
- 새 host 전환

### 근본 수정

원인과 구조적 취약점을 해결합니다.

- 배포 gate 추가
- resource budget 수정
- secret scope 축소
- query·schema 변경
- alert·runbook 개선

완화가 성공했다고 사고를 바로 종료하지 않습니다.

## 9. Runbook 구조

좋은 runbook은 긴 배경 설명보다 안전한 의사결정 경계를 제공합니다.

```text
제목과 대상 증상
사용자 영향
자동 경보와 확인 방법
필요 권한·도구
사전 안전 조건
가장 싼 진단 순서
가역 완화
위험한·파괴적 조치의 승인 조건
복구 절차
외부 사용자 경로 검증
중단·escalation 조건
수집할 증거
후속 작업
```

명령만 나열하지 않고 **기대 출력과 다음 분기**를 적습니다.

## 10. 필수 runbook

전체 목록과 공통 사용 규칙은 [운영 Runbook 색인](runbooks/00-index.md)에서 확인합니다.

### [502·504](runbooks/01-502-504-upstream-failure.md)

- 외부 DNS·TLS
- gateway log
- upstream DNS·port
- app process·readiness
- dependency timeout
- 최근 release

### [Database 인증 실패](runbooks/02-database-authentication-failure.md)

- secret 이름·version
- DB 사용자 존재와 권한
- old/new credential 회전 상태
- connection pool reload
- 값 자체를 출력하지 않는 검증

### [Disk 고갈](runbooks/03-disk-exhaustion.md)

- byte와 inode
- 증가 원인
- 안전하게 지울 수 있는 cache·old log
- DB·upload·backup 정본 보호
- 자동 prune 금지 경계

### [인증서 만료·갱신 실패](runbooks/04-certificate-renewal-failure.md)

- 외부 제공 인증서
- ACME 최근 결과
- DNS/HTTP challenge
- 새 파일 검증
- gateway reload

### [Container restart loop](runbooks/05-container-restart-loop.md)

- exit code
- 최초 오류
- OOM 여부
- config·secret
- schema 호환
- rollback 조건

### [잘못된 배포](runbooks/06-bad-deployment-rollback.md)

- 배포 잠금
- current/previous manifest
- schema 호환
- rollback 또는 roll-forward 판단
- smoke와 관찰 창

### [Backup 실패](runbooks/07-backup-job-failure.md)

- 마지막 성공 backup
- staging disk
- DB dump 오류
- 암호화·upload
- RPO 위험 평가

### [데이터 복원](runbooks/08-data-restore.md)

- 격리된 대상
- backup manifest 검증
- 외부 효과 차단
- 사용자 경로 검사
- 전환 승인

### [Host 재구축](runbooks/09-host-rebuild.md)

18장의 capstone을 runbook으로 유지합니다.

### [Secret 유출](runbooks/10-secret-compromise.md)

- 노출 scope·window
- 신뢰할 수 있는 별도 관리 경로
- 폐기·재발급·소비자 전환
- Host·CI 신뢰 재설정
- Git·로그·artifact 잔존 처리

## 11. 파괴적 명령의 안전 장치

다음 명령은 대상과 영향이 명확하지 않으면 실행하지 않습니다.

```text
docker compose down -v
docker system prune -a
rm -rf
database DROP/TRUNCATE
firewall 전체 교체
DNS zone 대량 변경
backup retention 삭제
```

안전 장치:

- production 환경 명시
- 대상 resource ID 출력
- dry-run
- backup·복구 지점 확인
- 두 번째 승인
- 명시적인 확인 문자열
- 실행 뒤 검증

script의 `--force`가 위험을 이해했다는 증거는 아닙니다.

## 12. 의사소통

사용자 update 예:

```text
12:10 KST부터 메모 작성 요청이 실패하고 있습니다.
읽기 기능은 정상입니다. 현재 쓰기 요청을 제한하고 데이터베이스 연결 상태를 복구 중입니다.
다음 update는 12:40 KST에 게시하겠습니다.
```

피해야 할 것:

- 확인되지 않은 원인 단정
- 내부 secret·취약점 상세 공개
- 근거 없는 복구 시각 약속
- update 없이 긴 침묵

복구 후 사용자 영향 시간과 데이터 상태를 명확히 알립니다.

## 13. 보안 사고 추가 경계

credential 탈취나 악성 image 가능성이 있으면 일반 장애와 다르게 대응합니다.

- 손상 가능 host에서 새 secret 생성 금지
- 별도 신뢰 장치에서 credential 폐기·재발급
- registry provenance와 digest 검증
- backup의 공격 이전 시점 확인
- 접속·변경 로그 보존
- 법적·개인정보 통지 요구 검토

공격자가 현재 host를 제어할 수 있다면 그 host의 로그와 검사 결과를 완전히 신뢰하지 않습니다.

## 14. 복구 확인

내부 상태만 보지 않습니다.

```text
외부 DNS·TLS
→ 핵심 읽기
→ 안전한 쓰기
→ background 처리
→ error·latency 안정화
→ 데이터 정합성
→ 경보 정상화
```

경보가 사라진 것만으로 복구를 확정하지 않습니다. 경보 시스템 자체가 고장 났을 수 있습니다.

## 15. 사고 종료 조건

- 사용자 핵심 기능이 운영 목표 안으로 복구됨
- 데이터 손실·보안 영향 범위가 평가됨
- 임시 완화의 소유자와 만료 시점이 있음
- monitoring이 정상 작동함
- 자동 배포와 변경 동결 해제 조건이 충족됨
- timeline과 후속 작업이 보존됨

원인 분석이 완전히 끝나지 않아도 사용자 사고를 종료할 수 있지만, investigation 작업을 별도로 남깁니다.

## 16. 사후 검토

비난보다 시스템과 결정 조건을 분석합니다.

```text
무슨 일이 일어났는가?
사용자와 데이터 영향은 무엇인가?
어떻게 감지됐는가?
무엇이 대응을 도왔는가?
무엇이 대응을 지연시켰는가?
어떤 방어가 실패했는가?
어떤 위험을 알고 수용했는가?
재발 가능성과 영향도를 무엇으로 줄일 것인가?
```

후속 작업에는 owner, 기한과 검증 방법이 필요합니다.

나쁜 작업:

> 모니터링을 개선한다.

좋은 작업:

> 외부 쓰기 synthetic check를 추가하고 5분 지속 실패 시 SEV-2 경보를 발생시킨다. 담당 A, 8월 21일, staging failure injection으로 검증.

## 17. Runbook 검증

실제 사고만 기다리지 않습니다.

- table-top exercise
- staging failure injection
- backup restore drill
- expired certificate simulation
- disk pressure simulation
- bad release rollback
- operator가 문서만 보고 수행

명령이나 UI가 바뀌어 실행되지 않으면 runbook은 운영 자산이 아닙니다.

## 18. 실습

[`exercises/17-incident-response`](../exercises/17-incident-response/)은 배포 뒤 502, DB connection 고갈과 disk 증가가 겹친 timeline을 제공합니다.

학습자는 다음을 작성합니다.

1. 관찰 사실과 가설 분리
2. 사용자 영향 기반 심각도
3. 지휘·운영·소통 역할
4. 최초 안전 조치
5. 증거를 지우는 위험한 조치 거부
6. 완화와 근본 수정 분리
7. 복구 검증 조건
8. owner·기한·검사 방법이 있는 후속 작업

자동 검사는 정답 원인 하나보다 사고 대응의 안전한 순서와 근거를 확인합니다.

## 19. 공식 확인 자료

- CISA Incident Response resources: <https://www.cisa.gov/topics/cyber-threats-and-advisories/incident-response>
- NIST SP 800-61 Rev. 3, Incident Response Recommendations: <https://csrc.nist.gov/pubs/sp/800/61/r3/final>
- Docker daemon troubleshooting: <https://docs.docker.com/engine/daemon/troubleshoot/>

다음 장에서는 지금까지 만든 계약을 사용해 기존 host가 전혀 없는 상태에서 공개 서비스를 복구합니다.
