# 공개 서비스 재구축 계획

기존 host를 사용할 수 없다는 전제로 rebuild plan과 증거 계약을 작성합니다. 자동 검사는 실제 VPS를 만들지 않지만, 위험한 순서와 숨은 정본 의존성을 찾아냅니다.

관련 문서: [`docs/18-production-rebuild-capstone.md`](../../docs/18-production-rebuild-capstone.md)

## 작성 대상

```text
skeleton/rebuild-plan.yaml
```

필수 내용:

- exact image digest와 rollback digest
- 외부 backup ID·manifest checksum
- secret 값이 아닌 versioned 이름과 원본
- 안전한 stage 순서
- 각 stage의 owner·중단 조건·증거
- DNS 전환 전 restore와 internal smoke
- 인증서 검증을 끄지 않은 external smoke
- 실제 RPO·RTO 측정 시각
- alert 전달 시험
- 잘못된 image, 누락 secret, 손상 backup, hostname 불일치, disk 부족, bad release failure drill

## 검증

```sh
cd exercises/18-production-rebuild
./verify.sh skeleton
./verify.sh reference
```

자동 검사를 통과한 뒤에만 폐기 가능한 실제 VPS에서 runbook을 실행합니다. 실제 secret, 개인키와 production backup은 repository에 넣지 않습니다.

## 완료 기준

- [ ] `./verify.sh skeleton`이 통과하고 image·backup·secret의 외부 정본과 checksum 또는 version 식별자가 모두 구체적이다.
- [ ] 각 stage에 owner·중단 조건·증거가 있으며 restore와 internal smoke가 DNS 전환보다 앞서고 external smoke는 TLS 검증을 유지한다.
- [ ] 모든 failure drill의 안전한 중단·복구 경로와 관측 시각으로 계산한 실제 RPO·RTO, alert 전달 결과를 기록한다.

## 자기 설명

1. 기존 host를 잃은 상황에서 repository 밖에 반드시 존재해야 하는 정본과 접근 권한은 무엇인가?
2. DNS 전환을 restore·internal smoke보다 뒤에 두어야 사용자 영향과 rollback 선택지가 어떻게 달라지는가?
3. 프로세스 기동 성공이 아니라 어떤 외부 기능·데이터·관측 증거가 있어야 재구축 완료를 선언할 수 있는가?
