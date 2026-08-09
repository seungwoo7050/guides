# 기여 안내

이 브랜치는 코딩 에이전트를 사용하는 법보다 에이전트 런타임을 개발하는 법을 설명합니다. 코딩 에이전트가 주 구현 프로필이지만 core model·RAG·tool·state·policy·evaluation contract는 도메인 중립적으로 유지합니다. 문서, starter/reference, fixture, 실습과 검증 기준은 같은 책임과 실패를 가리켜야 합니다.

## 문서를 고칠 때

- 모델의 자연어 능력보다 runtime의 상태·권한·도구·증거를 먼저 설명합니다.
- 특정 제품의 UI나 현재 옵션을 보편 원리처럼 고정하지 않습니다.
- 카탈로그의 필수 `python`·`web-app`, 권장 `distributed-services`·`cybersecurity`·`machine-learning`이 소유한 일반 원리는 반복하지 않고 에이전트 접점만 설명합니다. Git·Unix 구현 역량은 필요할 수 있지만 catalog relation을 임의로 바꾸지 않습니다.
- 정상 경로뿐 아니라 unauthorized RAG source, stale context, 부분 적용, command timeout, 기존 실패, 취소, budget 소진과 resume을 포함합니다.
- “잘 작동한다”, “안전하다”, “자율적이다” 같은 주장은 판정 조건과 근거 없이 쓰지 않습니다.
- 모델 출력과 실제 authority, 계획과 실행, 완료 선언과 verifier 판정을 구분합니다.

## 실습 설계를 고칠 때

실습은 다음을 포함해야 합니다.

```text
목표
초기 상태
구현할 책임
입력·출력·상태
정상·경계·실패 시나리오
완료 판정
필수 산출물
의도적 비범위
starter/reference/fixture와 canonical test
```

실습이 특정 framework나 model provider 없이는 성립하지 않게 만들지 않습니다. provider adapter와 runtime contract를 분리하고 필수 검증은 scripted adapter와 loopback provider fixture로 수행합니다. starter는 의도한 미완성 경계에서 실패하고 reference는 같은 공개 검사에서 통과해야 하며, known-bad는 관련 실패 이유로 거부되어야 합니다.

RAG 변경은 retrieval 전에 principal·resource 권한을 적용하고 source origin·revision·digest citation을 보존해야 합니다. 권한 없는 source를 검색한 뒤 display에서만 가리는 구현은 허용하지 않습니다.

## Capstone을 고칠 때

Capstone의 중심은 저장소를 실제로 조사·편집·실행·검증하는 반복 루프입니다. 다음을 축소해 단일 patch 과제로 되돌리지 않습니다.

- 저장소 discovery
- Git 기준점과 변경 격리
- 여러 파일 편집
- process 실행과 취소
- test/build 결과 해석
- 실패 뒤 재계획
- 사용자 승인과 interruption
- checkpoint·resume·cancel과 effect reconciliation
- model·tool·비용·실행 시간 budget
- 권한 인지 retrieval과 source citation
- 외부 verifier

원격 push, merge, 배포, multi-agent와 cloud scheduling은 선택 확장으로 유지합니다.

실제 provider live smoke는 선택이며 credential·network·비용이 없다는 이유로 필수 reference 검사를 skip해서는 안 됩니다. 반대로 loopback fixture 통과를 실제 provider 품질이나 production 안전성의 증거로 표현하지 않습니다.

## 변경 확인

```sh
./prepare.sh
./verify.sh
make test-reference
make test-starter-contract
make test-mutants
make test-capstone
git diff --check
```
