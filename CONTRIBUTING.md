# 기여 안내

문서, 예제와 검증기는 같은 플랫폼 계약을 가리켜야 합니다. 새로운 도구를 추가하기 전에 어떤 사용자 문제와 실패 경계를 소유하는지 먼저 설명해 주세요.

## 글을 고칠 때

- 설명은 자연스러운 한국어 경어체로 작성합니다.
- API, command, resource kind와 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 영문 용어는 공식 문서를 찾는 데 도움이 될 때 첫 등장에 함께 적습니다.
- `web-infra`, `distributed-services`, `cybersecurity` 등 다른 브랜치가 소유한 기초 설명을 복사하지 않습니다.
- 특정 cloud provider나 제품 기능을 플랫폼 엔지니어링의 보편 원리처럼 단정하지 않습니다.
- 측정하지 않은 생산성, 안정성, 비용 절감 효과를 주장하지 않습니다.
- 실제 실행으로 확인하지 않은 예제는 설계 예시 또는 의사 코드라고 명시합니다.
- 날짜와 버전에 따라 달라지는 기능은 공식 문서와 적용 환경을 함께 기록합니다.

## 실습을 고칠 때

- 핵심 실습은 `contract.json`으로 완료 조건을 선언합니다.
- `skeleton`은 의도한 누락 때문에 실패해야 합니다.
- `reference`는 같은 검사에 통과하고 `TODO`, `TBD`, `미정`을 남기지 않습니다.
- 검사기는 정답 문구 전체를 비교하지 않고 필수 상태·책임·실패·검증 항목을 확인합니다.
- 실제 cloud 또는 cluster 실습은 핵심 완료 조건이 아니라 `docs/90-optional-labs/`에 둡니다.
- credential, kubeconfig, state, private key, generated artifact와 실행 로그를 추적하지 않습니다.

## 변경 확인

```sh
./prepare.sh
make check
./verify.sh
```

`make check`는 현재 문서와 계약의 정적 무결성을 확인합니다. 최종 판정은 준비 fingerprint, reference·skeleton의 positive/negative 검사까지 포함하는 `./verify.sh`를 사용합니다.

커밋 전에는 다음을 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 커밋

Conventional Commits 형식을 사용합니다.

```text
docs(platform): tenant isolation 경계 보완
test(platform): reconciliation skeleton 부정 검사 추가
fix(platform): source fingerprint에서 workspace 제외
```

서로 다른 사용자 계약이나 실패 모델을 바꾸는 수정은 별도 커밋으로 나눕니다.
