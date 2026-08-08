# 백업, 복원과 재해 복구

백업 작업의 종료 코드가 0이라는 사실만으로 데이터가 복구 가능하다고 말할 수 없습니다. 운영에서 필요한 것은 파일 생성이 아니라 다음 전체 경로입니다.

```text
복구할 상태 식별
→ 일관된 시점의 데이터 획득
→ 무결성 확인
→ 호스트 밖으로 전송
→ 보존·암호화·삭제 권한 분리
→ 빈 환경에 복원
→ 애플리케이션 기능 검증
→ RPO·RTO 증거 기록
```

대응 실습은 [`exercises/15-disaster-recovery`](../exercises/15-disaster-recovery/)입니다.

## 1. 백업과 가용성은 다른 문제

백업은 손실된 상태를 과거 시점에서 복원합니다. replica나 두 번째 호스트는 장애 중 서비스를 계속 제공할 수 있지만 잘못된 삭제, 손상과 ransomware가 replica에도 복제될 수 있습니다.

```text
가용성 장치: 장애 중 서비스를 계속 제공
백업: 과거의 독립된 상태로 되돌림
```

둘 중 하나가 다른 하나를 대체하지 않습니다. 이 과정은 단일 호스트이므로 즉시 failover보다 검증된 복원을 기준선으로 둡니다.

## 2. 복구 대상 목록

호스트 전체를 막연히 백업하지 말고 상태별 복구 원본을 정합니다.

| 상태 | 복구 원본 | 일반적인 방법 |
|---|---|---|
| 애플리케이션 image | registry | exact digest pull |
| Compose·gateway 설정 | Git 또는 release artifact | versioned checkout |
| 공개 환경 설정 | deployment repository | versioned file |
| runtime secret | secret 원본 | 재주입 또는 재발급 |
| database | 외부 backup storage | DB dump·physical backup |
| 사용자 업로드 | object backup | file snapshot·sync |
| TLS 인증서 | ACME 재발급 또는 보호된 저장소 | 새 발급 우선 고려 |
| DNS record | provider와 versioned record 문서 | API·관리 console |
| 운영 로그 | 외부 log store | 보존 정책에 따라 조회 |
| release history | deployment record | manifest 복원 |

image와 설정을 데이터 backup에 중복해 넣을 수는 있지만, 무엇이 정본인지 하나로 정합니다.

## 3. 일관된 백업

실행 중인 데이터 파일을 무작정 복사하면 서로 다른 시점의 page와 log가 섞일 수 있습니다. 데이터베이스가 제공하는 일관된 dump, physical backup 또는 filesystem snapshot 절차를 사용합니다.

### 논리 백업

예: SQL dump

장점:

- 내용을 비교적 쉽게 검사할 수 있습니다.
- 다른 instance에 복원하기 쉽습니다.
- schema와 data를 선택할 수 있습니다.

주의:

- 큰 데이터에서는 생성·복원 시간이 길 수 있습니다.
- DB별 option과 권한을 알아야 합니다.
- transaction 일관성 option을 사용해야 합니다.

### 물리 백업

data file과 WAL·redo log를 DB가 정의한 방식으로 보존합니다.

장점:

- 큰 데이터의 빠른 복원과 시점 복구에 유리할 수 있습니다.

주의:

- DB version·storage layout 의존성이 큽니다.
- 단순 디렉터리 copy와 다릅니다.
- 복구 도구와 log 보존 계약이 필요합니다.

초기 작은 서비스에서는 논리 백업으로 시작해 실제 RTO를 측정하고 부족할 때 물리 백업을 검토합니다.

## 4. 데이터베이스와 업로드의 같은 시점

데이터베이스가 업로드 파일의 경로를 가리킨다면 둘의 시점이 다를 때 다음 문제가 생깁니다.

- DB row는 있지만 파일이 없음
- 파일은 있지만 DB row가 없음
- 파일 version과 metadata가 다름

선택지:

- write를 잠시 정지하고 둘을 같은 window에 백업
- application-level snapshot ID를 기록
- upload를 content-addressed immutable object로 저장
- DB와 object store의 versioning·보존 정책 연결
- 복원 뒤 reconciliation 수행

완벽한 원자 snapshot이 어렵다면 불일치 탐지와 복구 정책을 명시합니다.

## 5. 백업 artifact와 manifest

각 백업에 machine-readable manifest를 둡니다.

```yaml
schema_version: 1
backup_id: 2026-08-07T020000Z
created_at: 2026-08-07T02:00:00Z
source:
  service: notes
  release: 2026-08-01.2
  database_schema: 18
artifacts:
  - path: database.sql.gz.enc
    sha256: ...
    bytes: 123456
  - path: uploads.tar.zst.enc
    sha256: ...
    bytes: 987654
consistency:
  method: maintenance-window
  started_at: ...
  completed_at: ...
```

Manifest에는 다음을 넣지 않습니다.

- 암호화 key
- database password
- 사용자 개인정보의 원문
- 복호화 credential

checksum은 우발적 손상 탐지에 사용합니다. 공격자가 artifact와 manifest를 모두 바꿀 수 있는 환경에서는 서명이나 변경 불가능한 저장소 정책이 필요합니다.

## 6. 암호화와 키 분리

백업에는 production 데이터가 그대로 포함됩니다. 전송 중과 저장 시 암호화를 적용하고, 복호화 key의 수명 주기를 별도로 관리합니다.

피해야 할 구조:

```text
production host
  ├─ backup file
  └─ 유일한 복호화 key
```

호스트가 손상되면 둘 다 유출되거나 삭제될 수 있습니다.

검토할 것:

- key 원본의 소유자
- 복구 담당자가 key에 접근하는 방법
- key rotation과 오래된 backup 복호화
- key 손실 시험
- 비상 접근 감사

## 7. 호스트 밖의 독립된 복사본

로컬 volume과 같은 host의 `/var/backups`만 사용하면 disk·host 손실에서 보호되지 않습니다. backup staging은 가능하지만 성공 후 외부 저장소로 전송합니다.

외부 저장소 정책:

- production credential과 다른 삭제 권한
- versioning 또는 object lock 검토
- retention 정책
- 전송 실패 경보
- 저장소 자체의 접근 로그
- 다른 계정·region 또는 offline copy 필요성
- 비용과 egress 제한

한 운영 credential이 production 데이터와 모든 backup을 동시에 삭제할 수 있다면 blast radius가 큽니다.

## 8. 보존 정책

예시:

```text
일별 14개
주별 8개
월별 12개
```

숫자를 그대로 복사하지 않습니다. 다음을 기준으로 정합니다.

- 오류 발견까지 걸리는 시간
- 법적·업무 보존 요구
- 저장 비용
- schema와 application 호환성
- 복원 시험 범위
- 사용자 삭제 요구

오래된 backup을 많이 보존할수록 개인정보와 credential 노출 범위도 커질 수 있습니다.

## 9. 백업 작업의 성공 조건

다음이 모두 확인돼야 합니다.

1. DB 도구 종료 코드 성공
2. artifact가 비어 있지 않음
3. 예상 table·record 또는 metadata 존재
4. checksum 계산 성공
5. 암호화 성공
6. 외부 저장소 upload 성공
7. 원격 object 크기·checksum 또는 provider 검증 성공
8. manifest 기록
9. backup age metric 갱신
10. 실패 시 경보

파이프라인에서 앞 명령 실패가 뒤 명령 때문에 가려지지 않도록 shell의 pipe 실패 처리와 임시 파일 원자 교체를 사용합니다.

## 10. 복원은 별도 환경에서 시작

처음부터 손상된 production 위에 덮어쓰지 않습니다.

```text
빈 복원 대상 준비
→ image·설정·secret version 확인
→ backup checksum·서명 검증
→ 복호화
→ DB와 파일 복원
→ schema·row count·업로드 정합성 검사
→ application을 격리된 주소로 실행
→ 기능 smoke test
→ 전환 여부 결정
```

복원 실패가 원본과 기존 backup을 손상하지 않게 read-only 원본에서 작업합니다.

## 11. 복원 검증

파일이 풀렸다는 것보다 사용자 기능을 봅니다.

- 핵심 table과 constraint가 있는가?
- 대표 row와 최근 데이터가 예상 범위인가?
- 업로드 checksum이 맞는가?
- 애플리케이션이 로그인·읽기·쓰기 가능한가?
- background job이 중복 실행되지 않는가?
- schema version이 release와 호환되는가?
- secret이 backup 시점의 폐기된 credential에 묶여 있지 않은가?

복원 환경에서 외부 email·결제·webhook을 실제로 보내지 않도록 차단합니다.

## 12. RPO 측정

장애 시각과 복원된 최신 event 시각을 비교합니다.

```text
실제 데이터 손실 범위
= 장애 직전 마지막 성공 write 시각 - 복원된 최신 write 시각
```

마지막 backup 생성 시각만 보고 계산하지 않습니다. backup이 실제로 외부 저장·검증된 시각과 복원된 데이터의 최신 시점을 봅니다.

## 13. RTO 측정

다음 구간을 기록합니다.

```text
장애 확인
→ 복구 결정
→ 새 환경 준비
→ artifact 획득
→ 복원
→ 검증
→ DNS·traffic 전환
→ 사용자 기능 확인
```

자동화가 빨라도 credential 승인이나 DNS 접근에 오래 걸릴 수 있습니다. 전체 경로를 측정합니다.

## 14. 재해 시나리오

### Host 전체 손실

registry, Git, secret 원본과 외부 backup에서 새 host를 구성합니다. 18장의 capstone입니다.

### 잘못된 데이터 삭제

현재 DB가 정상 실행 중이어도 과거 시점 복원이 필요합니다. 별도 DB에 복원하고 필요한 record를 선택적으로 회수할지 전체 전환할지 결정합니다.

### Ransomware 또는 관리자 credential 탈취

현재 host에서 생성한 새 backup을 신뢰할 수 없을 수 있습니다. 공격 이전의 변경 불가능하거나 offline backup과 깨끗한 provisioning 원본이 필요합니다.

### Backup 저장소 손상

다른 계정·region 또는 offline copy가 필요한지 운영 계약에서 정합니다.

### 암호화 key 손실

backup artifact가 있어도 복원할 수 없습니다. key 복구와 비상 접근을 별도로 시험합니다.

## 15. 복원 훈련

최소한 다음을 기록합니다.

```text
훈련 일시
사용 backup ID
복원 대상 환경
작업자
시작·종료 시각
복원된 최신 데이터 시점
검증한 사용자 경로
발견한 누락·수동 단계
실제 RPO·RTO
후속 조치와 담당자
```

같은 사람이 같은 익숙한 host에서만 반복하면 숨은 전제를 발견하기 어렵습니다. 가능한 경우 다른 작업자나 새 환경에서 수행합니다.

## 16. 실습

[`exercises/15-disaster-recovery`](../exercises/15-disaster-recovery/)은 합성 database dump와 업로드를 사용합니다.

학습자는 다음을 구현합니다.

1. source 상태를 읽기 전용으로 취급
2. artifact별 checksum과 size를 manifest에 기록
3. 완성 전 backup을 current로 노출하지 않음
4. 손상된 artifact 복원 거부
5. 빈 대상에만 기본 복원
6. DB row와 upload checksum의 참조 정합성 검사
7. 복원 뒤 사용자 수준 smoke 검증
8. 실제 RPO·RTO 결과 기록

실제 개인정보나 production credential은 사용하지 않습니다.

## 17. 공식 확인 자료

- CISA StopRansomware Guide: <https://www.cisa.gov/stopransomware/ransomware-guide>
- NIST contingency planning: <https://csrc.nist.gov/topics/security-and-privacy/security-programs-and-operations/contingency-planning>
- MariaDB backup and restore overview: <https://mariadb.com/docs/server/server-usage/backing-up-and-restoring-databases/>

다음 장에서는 장애가 나기 전 자원 고갈을 예측하고, base image·host·Docker를 안전하게 갱신하는 운영 주기를 만듭니다.
