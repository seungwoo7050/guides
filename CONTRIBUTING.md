# 기여 안내

문서의 설명, skeleton의 실패와 reference의 동작은 같은 계약을 가리켜야 합니다. 정상 입력만 확인하지 말고 잘못된 입력, 경계값, 중간 실패와 종료 경로까지 재현해 주세요.

## 글을 고칠 때

- 설명은 자연스러운 한국어 경어체로 작성합니다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 다른 장이 소유한 개념은 필요한 만큼만 복습하고 같은 설명을 복제하지 않습니다.
- 새 개념은 사용하기 전에 소개하거나 선행 문서를 명시합니다.
- 성능과 안정성 주장은 실행한 명령, 환경과 관찰값이 있을 때만 작성합니다.
- 필수 학습 내용은 `docs/`, `examples/`, `exercises/` 안에서 완결합니다.

## 코드를 고칠 때

- 짧고 독립적인 관찰 코드는 `examples/`에 둡니다.
- 구현 문제는 `exercises/` 아래에 `skeleton`과 `reference`를 함께 둡니다.
- `skeleton`은 컴파일할 수 있어야 하며 테스트가 계약 위반 때문에 실패해야 합니다.
- `reference`에는 `TODO`, 임시 반환값이나 무시한 예외를 남기지 않습니다.
- 동시성 검사는 `sleep`의 우연한 순서에 기대지 않고 latch, barrier나 제어 가능한 실행기를 사용합니다.
- 검사기는 소스 문구보다 외부에서 관찰 가능한 상태, 반환값과 효과를 확인합니다.
- 임시 파일과 프로세스는 성공·실패·인터럽트 경로에서 모두 정리합니다.
- 원본 `skeleton`은 지정 실패를 증명하는 배포 fixture로 유지합니다. 학습자 구현은 `./scripts/new-workspace.sh exercises/<경로>`로 만든 `.workspace/` 복사본에서 수행하고 `./scripts/check-workspace.sh exercises/<경로>`로 같은 공개 테스트를 실행합니다.

## 변경 확인

공개 명령 네 가지를 저장소 루트에서 실행합니다.

```sh
make prepare
make check
VERIFY_LOG=/tmp/guide-java-verify.log make verify
make clean
```

`make prepare`는 의존성을 준비하고, `make check`는 빠른 정적·계약 검사를 실행합니다. `make verify`는 준비된 Maven 저장소를 오프라인으로 사용해 현재 working tree와 `.workspace/`를 외부에 복사하고 원본 불변성을 확인합니다. 필수 검사가 실행되지 못하면 성공으로 기록하지 않습니다. `make clean`은 명시된 빌드 생성물만 지우며 `.guide/java/` 준비 캐시와 학습자 `.workspace/`를 보존합니다.

커밋 전에는 추적 범위와 공백 오류를 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```
