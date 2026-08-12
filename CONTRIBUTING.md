# 기여 안내

문서, skeleton, reference와 검증 코드는 같은 계약을 가리켜야 합니다. 설명만 맞거나 reference만 통과하는 변경은 완료된 변경으로 보지 않습니다.

## 글을 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 각 문서는 문제, 보장 범위, 실패 조건과 검증 방법을 분리합니다.
- 다른 가이드가 소유하는 Java·데이터베이스·Spring·인프라 기초는 필요한 만큼만 연결합니다.
- “정확히 한 번”, “안전함”, “빠름” 같은 표현은 관찰할 상태와 검사를 함께 제시할 때만 사용합니다.
- 특정 제품 설정과 프레임워크 API는 안정된 분산 시스템 원리와 분리합니다.

## 실습을 고칠 때

- 구현 문제에는 `skeleton`과 `reference`를 함께 둡니다.
- 두 구현은 같은 공개 API와 같은 검사 파일을 사용해야 합니다.
- skeleton은 컴파일되지만 최소 한 개 이상의 핵심 계약 검사에서 실패해야 합니다.
- reference에는 `TODO`, 임시 반환값과 무조건 성공시키는 우회 코드를 남기지 않습니다.
- 출력 문자열이나 소스 모양보다 최종 업무 상태와 부정 불변 조건을 검사합니다.
- 시각과 네트워크 실패는 실제 대기보다 가상 시계와 결정적 실패 주입을 우선합니다.
- 임시 Git 저장소, 프로세스와 컨테이너는 고유한 디렉터리와 이름을 사용하고 종료 경로마다 정리합니다.

## 변경 확인

저장소 루트의 공개 명령 네 가지를 사용합니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-distributed-services-verify.log make verify
make clean
```

`make prepare`의 Maven cache 준비용 복사본은 learner `.workspace/`를 제외합니다. 반면 `make verify`는 현재 working tree와 `.workspace/`를 모두 외부에 복사하고 bytes·mode·symlink와 Git index의 전후 불변성을 확인하되, exact curriculum validator와 reference/skeleton 계약 검사는 canonical tracked curriculum만 대상으로 합니다. 학습자용 workspace는 `./scripts/new-workspace.sh <slug>`로 만들며 이 명령은 기존 destination과 symlink를 덮어쓰지 않습니다. `./scripts/verify-java.sh .workspace/<slug>`도 workspace 안의 수정 가능한 테스트가 아니라 해당 실습의 추적된 정본 테스트를 사용합니다. `make clean`은 명시된 생성물만 지우며 준비 cache와 learner `.workspace/`는 보존합니다.

커밋 전에는 추적 범위와 공백 오류를 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 커밋

제목은 Conventional Commits 형식을 사용합니다.

```text
docs(consistency): 재조정 종료 조건 보완
test(resilience): 전체 시간 예산 초과 검사 추가
fix(exercise): 중복 전달 뒤 효과 횟수 보존
```

문서와 그 계약을 검증하는 코드는 같은 커밋에 포함할 수 있습니다. 서로 독립적인 학습 단계는 나누어 기록합니다.
