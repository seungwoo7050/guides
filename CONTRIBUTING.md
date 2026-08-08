# 기여 안내

설명과 실행 결과는 같은 계약을 가리켜야 합니다. 문서 변경은 해당 예제나 상태 모델의 검증과 함께 확인합니다.

## 글을 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 메커니즘, 정책, 상태, 불변식과 관측값을 섞지 않습니다.
- 컴퓨터 구조, C/POSIX 구현과 Unix 관찰 가이드가 주 소유하는 내용은 필요한 만큼만 연결합니다.
- 특정 커널이나 CPU에서만 성립하는 구현 세부를 일반 원리처럼 단정하지 않습니다.
- 성능 수치는 실행 환경, 입력과 측정 방법을 함께 기록합니다.

## 코드를 고칠 때

- 사용자 공간에서 관찰할 수 있는 작은 독립 프로그램은 `examples/`에 둡니다.
- 운영체제 정책과 상태 전이는 `exercises/kernel-model/`에 결정론적으로 구현합니다.
- `skeleton`은 문법적으로 유효하고 구현할 책임을 드러내야 합니다.
- `reference`에는 `TODO`, 임시 반환값과 `NotImplementedError`를 남기지 않습니다.
- 정상 fixture뿐 아니라 잘못된 상태를 거부하는 failure fixture를 추가합니다.
- 검사기는 소스 문구보다 외부 상태, 반환값과 불변식 위반을 확인합니다.
- 학습자의 `workspace/`와 저장소 밖 파일을 자동으로 삭제하지 않습니다.

## 변경 확인

Python 3.12 이상과 C11 compiler가 있는 checkout에서 source를 바꾸지 않는 준비 검사를 실행합니다.

```sh
./prepare.sh
```

`prepare.sh`는 현재 HEAD·raw index·source의 파일/directory mode/symlink·실제 probe를 통과한 toolchain version을 ignored `.guide/` marker에 고정할 뿐, 문서·실습·workspace를 생성하거나 삭제하지 않습니다. 준비 뒤 source나 index가 바뀌었다면 다시 실행합니다.

최종 저장소 전체를 격리 복사본에서 검사합니다. 로그는 저장소 밖 절대 경로만 허용합니다.

```sh
./verify.sh
# 또는
VERIFY_LOG=/tmp/guide-os-verify.log ./verify.sh
```

빠른 개별 검사는 다음 명령으로 실행할 수 있습니다.

```sh
make check
make meta-check
make common-safety-check
make log-safety-check
make workspace-check
make -C examples check
make -C examples sanitizer-check
make -C exercises/kernel-model check
make signal-check
make checkpoint-check IMPL=reference CHECKPOINT=04-deadlock
```

새 checker 규칙에는 통과하는 reference test와 함께 그 규칙을 위반하는 mutant나 failure fixture를 추가합니다. 정상 fixture는 `expected` 결과를, failure fixture는 정확한 `expected_error`를 선언해야 합니다. checkpoint 이름은 `01-lifecycle`부터 `08-cli`까지의 공개 계약을 유지합니다.

커밋 전에는 추적 범위와 공백 오류를 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

서로 다른 정책이나 실습 단계를 한 커밋에 무리하게 섞지 않습니다. 문서와 그 동작을 확인하는 fixture·검사는 같은 변경 단위에 포함할 수 있습니다.
