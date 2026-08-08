# Runbook: Host 전체 재구축

## 대상 상황

- 기존 host에 접근할 수 없거나 신뢰할 수 없습니다.
- Local container, volume, shell history와 인증서를 복구 원본으로 사용할 수 없습니다.
- 외부 registry, Git, secret 원본, DNS 권한과 backup만 사용합니다.

이 runbook의 상세 단계와 평가 기준은 [18 공개 서비스 재구축 Capstone](../18-production-rebuild-capstone.md)을 따릅니다.

## 사전 결정

```text
사고인지 계획 훈련인지
기존 host를 신뢰할 수 있는지
선택 release와 backup
RTO·RPO 목표
새 public IP
Maintenance·status communication
작업자와 승인자
```

## 실행 단계

1. 복구 선언과 단계별 시각 기록
2. 새 Linux host·관리 경로·시간·disk 검증
3. Docker Engine·Compose와 firewall 준비
4. Exact release manifest·image digest 검증
5. Versioned secret 안전 주입
6. Backup checksum·복호화·격리 복원
7. Internal application smoke
8. Gateway와 public TLS 준비
9. A·AAAA와 DNS 전환
10. 외부 읽기·안전한 쓰기
11. Log·metric·alert 연결
12. Actual RPO·RTO 기록
13. Bad release·corrupt backup·missing secret drill
14. 기존 자산·credential 폐기

## 금지 사항

- `latest` tag 사용
- Production host에서 source build
- 기존 host 파일의 즉석 복사에 의존
- 검증 전 DNS 전환
- `curl -k` 성공만으로 TLS 완료 판정
- Backup 원본 덮어쓰기
- Secret을 evidence 문서에 기록

## 복구 확인

[18장 외부 기능 검증](../18-production-rebuild-capstone.md#11-stage-7-외부-기능-검증)과 관측 검증을 모두 완료합니다.

## 증거

```text
Provisioning version
Release·backup manifest digest
Image digest
TLS serial·expiry
DNS 전환 시각
단계별 시작·종료
외부 smoke
Alert test
Actual RPO·RTO
수동 개입과 후속 작업
```
