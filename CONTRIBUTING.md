# 기여 안내

이 브랜치는 코딩 에이전트를 사용하는 법보다 코딩 에이전트 런타임을 개발하는 법을 설명합니다. 문서, 실습 설계와 검증 기준은 같은 책임과 실패를 가리켜야 합니다.

## 문서를 고칠 때

- 모델의 자연어 능력보다 runtime의 상태·권한·도구·증거를 먼저 설명합니다.
- 특정 제품의 UI나 현재 옵션을 보편 원리처럼 고정하지 않습니다.
- `python`, `git`, `unix-systems`, `distributed-services`, `cybersecurity`가 소유한 일반 원리는 반복하지 않고 코딩 에이전트 접점만 설명합니다.
- 정상 경로뿐 아니라 stale context, 부분 적용, command timeout, 기존 실패, 취소와 resume을 포함합니다.
- “잘 작동한다”, “안전하다”, “자율적이다” 같은 주장은 판정 조건과 근거 없이 쓰지 않습니다.
- 모델 출력과 실제 authority, 계획과 실행, 완료 선언과 verifier 판정을 구분합니다.

## 실습 설계를 고칠 때

실습은 구현 코드를 요구하지 않아도 다음을 포함해야 합니다.

```text
목표
초기 상태
구현 또는 설계할 책임
입력·출력·상태
정상·경계·실패 시나리오
완료 판정
필수 산출물
의도적 비범위
```

실습이 특정 framework나 model provider 없이는 성립하지 않게 만들지 않습니다. provider adapter와 runtime contract를 분리합니다.

## Capstone을 고칠 때

Capstone의 중심은 저장소를 실제로 조사·편집·실행·검증하는 반복 루프입니다. 다음을 축소해 단일 patch 과제로 되돌리지 않습니다.

- 저장소 discovery
- Git 기준점과 변경 격리
- 여러 파일 편집
- process 실행과 취소
- test/build 결과 해석
- 실패 뒤 재계획
- 사용자 승인과 interruption
- 외부 verifier

원격 push, merge, 배포, multi-agent와 cloud scheduling은 선택 확장으로 유지합니다.

## 변경 확인

```sh
./prepare.sh
./verify.sh
git diff --check
```
