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
