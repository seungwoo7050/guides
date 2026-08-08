# Runbook: Backup 작업 실패

## 대상 증상과 사용자 영향

- 정기 backup job이 실패하거나 backup age 경보가 발생합니다.
- 서비스가 아직 정상이어도 RPO 위험이 증가합니다.
- 빈 파일이나 외부 전송되지 않은 로컬 artifact를 성공으로 오인할 수 있습니다.

## 사전 안전 조건

- 마지막 검증 backup과 manifest를 삭제하거나 덮어쓰지 않습니다.
- 실패한 staging artifact를 current backup으로 승격하지 않습니다.
- 복호화 key와 DB credential을 로그에 출력하지 않습니다.

## 1. 현재 RPO 위험 계산

기록:

```text
마지막 외부 저장·검증 성공 backup 시각
복원 시험에서 확인한 최신 data 시각
현재 시각
계약 RPO
```

단순 job 실행 시각이 아니라 실제 외부 artifact와 검증 결과를 사용합니다.

## 2. 단계별 실패 위치 확인

```text
DB snapshot·dump
→ Artifact size·content check
→ Compression
→ Encryption
→ Checksum·manifest
→ External upload
→ Remote verification
→ Retention
→ Metric·alert update
```

각 단계의 종료 코드와 임시 파일을 확인합니다. Shell pipeline에서 앞 단계 실패가 가려지지 않았는지 봅니다.

## 3. 자원 확인

```sh
df -h
df -i
```

- Staging disk와 inode
- DB connection·lock
- CPU·I/O pressure
- External storage quota·network
- Encryption key 접근
- Time synchronization

## 4. 원인 분기

### DB dump 실패

- DB health, 권한, transaction 일관성 option을 확인합니다.
- Schema upgrade 뒤 backup 도구 호환성을 봅니다.
- 실행 중 data directory를 일반 파일 복사로 대체하지 않습니다.

### Artifact가 비어 있거나 불완전

- 예상 table·row·object metadata 검사를 추가합니다.
- 임시 파일을 current 이름으로 rename하지 않습니다.

### Encryption·checksum 실패

- Key 접근과 tool version을 확인합니다.
- 평문 artifact의 staging 보존 시간을 최소화합니다.
- 실패했다고 암호화를 생략해 외부 전송하지 않습니다.

### External upload 실패

- Network, credential scope, object quota와 provider 오류를 확인합니다.
- Bounded retry와 timeout을 사용합니다.
- Local staging만 남았으면 host 손실 위험을 명시합니다.

### Retention 실패

- 삭제 권한과 object lock을 확인합니다.
- 최신 실패가 오래된 성공 backup 삭제로 이어지지 않게 순서를 분리합니다.

## 5. 가역 완화

- 원인을 수정한 뒤 새 backup ID로 재실행합니다.
- RPO가 임박하면 비필수 대형 쓰기나 batch를 제한할지 데이터 소유자와 결정합니다.
- External 저장소 장애면 승인된 두 번째 독립 저장소를 사용합니다.

같은 backup ID를 부분 artifact 위에 덮어쓰지 않습니다.

## 6. 복구 확인

- 새 artifact가 비어 있지 않습니다.
- Manifest의 size·checksum이 일치합니다.
- 외부 object가 검증됩니다.
- 별도 빈 환경의 restore smoke가 성공합니다.
- Backup age metric이 실제 성공 시각으로 갱신됩니다.
- 실패 경보가 resolve되고 test alert가 정상입니다.

## 7. 증거와 후속 작업

```text
마지막 성공·실패 backup ID
실패 단계와 종료 코드
RPO 위험 시간
새 artifact manifest·checksum
외부 저장 검증
Restore smoke 결과
재시도·quota·disk·alert 개선
```
