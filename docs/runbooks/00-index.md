# 운영 Runbook 색인

이 디렉터리는 공개 단일 호스트 서비스에서 반복 가능성이 높은 장애를 **증상별로 시작하는 절차**로 정리합니다. 각 runbook은 원인을 미리 단정하지 않습니다. 먼저 사용자 영향과 관찰 사실을 확인하고, 가장 값싼 검사부터 실패 경계를 좁힌 뒤, 되돌릴 수 있는 완화를 우선합니다.

## 사용 규칙

1. 현재 시각, 환경, release와 최초 증상을 기록합니다.
2. 동시에 여러 설정을 바꾸지 않습니다.
3. 명령을 실행하기 전에 대상 host·Compose project·service를 다시 확인합니다.
4. 데이터 삭제, volume 제거, firewall 전체 교체와 credential 폐기는 명시된 승인 경계에서만 수행합니다.
5. 완화 뒤에는 내부 상태가 아니라 외부 사용자 경로로 복구를 확인합니다.
6. 명령과 UI가 바뀌면 runbook을 즉시 수정하고 다음 훈련에서 다시 검증합니다.

## 공통 준비 정보

runbook을 사용하기 전에 다음 값을 안전한 운영 위치에서 확인합니다.

```text
환경 이름
공개 hostname
host 또는 instance ID
Compose project directory
현재 release manifest
이전 호환 release manifest
관측 dashboard와 log 위치
backup manifest 위치
incident communication 경로
```

실제 secret 값은 runbook이나 사고 timeline에 복사하지 않습니다.

## Runbook 목록

| 증상 | 문서 | 첫 분류 질문 |
|---|---|---|
| Gateway 502·504 | [01](01-502-504-upstream-failure.md) | Gateway까지 성공했고 어느 upstream 경계에서 실패했는가? |
| 데이터베이스 인증 실패 | [02](02-database-authentication-failure.md) | DB가 거부한 것인가, 잘못된 secret을 소비한 것인가? |
| Disk·inode 고갈 | [03](03-disk-exhaustion.md) | 무엇이 얼마나 빨리 증가하며 어떤 데이터는 삭제 불가능한가? |
| 인증서 만료·갱신 실패 | [04](04-certificate-renewal-failure.md) | 발급, 파일 교체, reload, 외부 제공 중 어디가 실패했는가? |
| Container restart loop | [05](05-container-restart-loop.md) | 종료 원인은 application, OOM, 설정, secret, schema 중 무엇인가? |
| 잘못된 배포 | [06](06-bad-deployment-rollback.md) | 이전 release가 현재 schema·설정과 호환되는가? |
| Backup 작업 실패 | [07](07-backup-job-failure.md) | 마지막 검증 backup과 현재 RPO 위험은 얼마인가? |
| 데이터 복원 | [08](08-data-restore.md) | 원본을 건드리지 않고 격리된 대상에 복원할 수 있는가? |
| Host 전체 손실 | [09](09-host-rebuild.md) | 외부 원본만으로 exact release와 데이터를 재구축할 수 있는가? |
| Secret 유출 | [10](10-secret-compromise.md) | 어떤 권한이 언제부터 노출됐고 무엇을 먼저 폐기해야 하는가? |

## 공통 중단 조건

다음 상황에서는 자동화나 개인 판단으로 계속 진행하지 않고 사고 지휘자 또는 데이터·보안 소유자에게 escalation합니다.

- 데이터 파괴 또는 정합성 위반 가능성이 있습니다.
- 현재와 이전 release 모두 호환되지 않습니다.
- host나 CI가 공격자에게 제어됐을 가능성이 있습니다.
- backup과 복호화 key의 무결성을 신뢰할 수 없습니다.
- DNS·registry·secret 원본의 관리 권한이 불분명합니다.
- 같은 조치를 반복했는데 결과가 달라집니다.
- 증거 보존과 사용자 영향 완화가 충돌합니다.

## 공통 복구 확인

```text
외부 DNS
→ TCP 443
→ TLS hostname·chain
→ Gateway
→ Application readiness
→ 핵심 읽기
→ 안전한 쓰기와 재조회
→ Background 처리
→ Error·latency 안정화
→ 경보 정상화
```

경보가 사라졌다는 사실만으로 복구를 확정하지 않습니다. 경보 수집 자체가 실패했을 수 있습니다.
