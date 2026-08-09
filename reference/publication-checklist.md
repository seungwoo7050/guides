# 브랜치 게시 전 검수

## 범위와 중복

- [ ] `web-infra`의 단일 서비스 운영 내용을 다시 가르치지 않습니다.
- [ ] `distributed-services`의 Saga·Outbox·업무 수렴을 복제하지 않습니다.
- [ ] `distributed-systems`의 consensus·replicated log를 이 과정의 필수 구현으로 만들지 않습니다.
- [ ] `cybersecurity`가 소유하는 공격·방어 전 과정을 반복하지 않습니다.
- [ ] Platform-specific 접점과 소유권 차이만 설명합니다.

## 문서

- [ ] 모든 내부 링크가 작동합니다.
- [ ] 용어와 파일 이름이 README·roadmap·문서에서 일치합니다.
- [ ] 도구 이름보다 상태·책임·실패·검증이 중심입니다.
- [ ] 버전에 민감한 내용은 공식 자료와 support status를 확인했습니다.
- [ ] 성능·보안·신뢰성 주장을 실제 evidence 없이 단정하지 않습니다.

## 실습

- [ ] 모든 reference가 계약을 통과합니다.
- [ ] 모든 skeleton은 같은 계약에서 의도대로 실패합니다.
- [ ] Contract가 특정 정답 문구보다 필수 상태를 검사합니다.
- [ ] 실제 cloud/cluster가 없는 실습의 한계를 명시합니다.
- [ ] 선택 실습에 credential·비용·cleanup 주의가 있습니다.

## 저장소

- [ ] `./prepare.sh && ./verify.sh`가 깨끗한 복사본에서 성공합니다.
- [ ] 실행 권한과 `.gitignore`가 맞습니다.
- [ ] 생성물·credential·state가 추적되지 않습니다.
- [ ] 라이선스와 기여 안내가 포함돼 있습니다.
- [ ] 압축 해제 뒤 최상위 디렉터리와 파일 mode가 유지됩니다.
