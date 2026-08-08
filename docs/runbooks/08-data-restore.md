# Runbook: 데이터 복원

## 대상 상황

- 잘못된 삭제·손상·host 손실 뒤 backup에서 데이터를 복원합니다.
- 전체 전환이 아니라 일부 record 회수만 필요할 수 있습니다.
- 복원은 현재 production을 덮어쓰는 명령이 아니라 별도의 검증 프로젝트입니다.

## 필요한 역할

- 사고 지휘자
- 데이터 소유자
- 복원 실행자
- 애플리케이션 검증자
- 외부 전환 승인자

한 사람이 여러 역할을 맡아도 결정과 실행을 구분합니다.

## 사전 안전 조건

- Backup 원본과 manifest를 read-only로 취급합니다.
- Production DB 위에 바로 restore하지 않습니다.
- Email, 결제, webhook과 background side effect를 격리합니다.
- 선택한 backup의 RPO 영향을 승인받습니다.

## 1. 복원 목표 정의

```text
전체 서비스 복구 또는 일부 data 회수
선택 backup ID
복원해야 할 최신 시각
대상 application release·schema
허용 중단 시간
전환 또는 merge 방식
```

## 2. Backup 검증

- Manifest schema와 서명·출처
- Artifact size·checksum
- 암호화 key 접근
- DB engine·version 호환성
- Upload snapshot과 DB snapshot 일관성
- Malware·침해 시점 위험

Checksum 실패 artifact를 강제로 복원하지 않습니다.

## 3. 격리된 대상 준비

```text
빈 database
빈 upload target
외부 network 제한
Production과 다른 project·volume 이름
안전한 test secret
Side effect disabled configuration
```

대상에 기존 data가 있으면 기본적으로 중단합니다. 덮어쓰기는 별도 승인합니다.

## 4. 복원 수행

```text
복호화
→ DB restore
→ Upload restore
→ Schema 확인
→ Constraint·row count
→ 참조 무결성·checksum
→ 호환 application 시작
```

복원 명령의 stdout·stderr와 종료 코드를 보존하되 secret과 개인정보를 redaction합니다.

## 5. 애플리케이션 검증

- 대표 사용자 로그인 또는 승인된 인증 대체
- 핵심 읽기
- 격리된 안전한 쓰기와 재조회
- Upload 조회
- Background job 중복 여부
- 최근 event 시각
- Schema·release 호환성

SQL row count만으로 사용자 복구를 확정하지 않습니다.

## 6. 전환 결정

### 전체 전환

- 쓰기를 정지하거나 변경분 처리 전략을 정합니다.
- 최종 delta 또는 maintenance window를 적용합니다.
- DNS·traffic 전환과 rollback 조건을 기록합니다.

### 일부 data 회수

- 어떤 record와 dependency를 회수할지 정의합니다.
- Application API 또는 검증된 migration을 사용합니다.
- Foreign key·audit·업무 불변식을 확인합니다.

Production DB에 ad-hoc SQL을 직접 적용하는 것을 기본값으로 두지 않습니다.

## 7. 복구 확인

- 외부 사용자 경로가 성공합니다.
- 복원된 최신 data 시각으로 실제 RPO를 계산합니다.
- 복구 선언부터 사용자 기능까지 실제 RTO를 계산합니다.
- Error·latency·background processing이 안정적입니다.
- 새 backup이 성공하고 이전 손상 상태와 분리됩니다.

## 8. 중단·escalation 조건

- Backup integrity를 신뢰할 수 없습니다.
- Schema 호환성이 확인되지 않습니다.
- 복원 data에 침해 흔적이 있습니다.
- 일부 회수가 다른 사용자·업무 기록을 손상할 수 있습니다.
- 실제 RPO가 승인 범위를 초과합니다.

## 9. 증거와 후속 작업

```text
선택 backup·release
Checksum·복원 종료 코드
복원된 최신 event
검증한 사용자 경로
실제 RPO·RTO
전환·merge 승인
누락된 자동화와 runbook 수정
```
