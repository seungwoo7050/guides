# 기여 안내

언어 구현 문서는 한 단계의 출력이 다음 단계의 입력 계약과 일치해야 합니다. lexer를 설명하면서 parser가 소비할 수 없는 token을 만들거나, type checker의 보장을 optimization이 임의로 확대하지 않도록 변경 전후의 phase contract를 함께 검토합니다.

## 글을 고칠 때

- 설명은 자연스러운 한국어 경어체 또는 일관된 서술체로 작성합니다.
- 명령, 문법 기호, opcode, API와 식별자는 원래 표기를 유지하고 백틱으로 구분합니다.
- 영문 용어는 표준 문서 검색에 도움이 될 때 첫 등장에 함께 적습니다.
- 다른 브랜치가 소유하는 알고리즘, ISA, 운영체제, 언어 문법 입문을 반복하지 않습니다.
- 예제 문법과 `Mica` capstone 명세가 다르면 어느 쪽이 설명용 축약인지 표시합니다.
- 성능, 최적화 효과, 진단 품질과 호환성을 측정 없이 단정하지 않습니다.
- parser가 받아들이는 문장과 언어가 의미 있게 허용하는 프로그램을 구분합니다.

## 코드를 고칠 때

- 한 개념만 관찰하는 완성 프로그램은 `examples`에 둡니다.
- 학습자가 완성할 작업은 `exercises`에 두고 입력·출력·실패·완료 조건을 문서화합니다.
- capstone `skeleton`은 의도적으로 미완성이며 명시된 종료 코드와 진단으로 실패해야 합니다.
- 답안 전체를 추가하려면 `reference`의 목적과 유지 비용을 먼저 기록하고, skeleton과 같은 conformance 검사에 통과시킵니다.
- 검사기는 소스 구조나 특정 함수 이름보다 CLI 계약과 관찰 가능한 결과를 확인합니다.
- source span, diagnostic code, AST/IR schema처럼 외부 도구가 소비하는 형식을 바꿀 때 fixture와 호환성 설명을 함께 수정합니다.
- 임시 파일과 workspace는 저장소 밖 또는 `.workspaces` 아래에 만들고 종료 경로마다 정리합니다.

## 변경 확인

빠른 문서·구조·예제 검사를 실행합니다.

```sh
make check
```

준비 상태와 source fingerprint까지 포함한 전체 검증은 다음과 같습니다.

```sh
./prepare.sh
./verify.sh
```

커밋 전에는 추적 범위와 공백 오류를 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

## 커밋

Conventional Commits 형식을 사용합니다.

```text
docs(parser): Pratt 결합력 설명 보완
test(mica): 잘못된 반환형 fixture 추가
fix(verifier): 외부 절대 링크를 상대 링크로 오인하지 않도록 수정
```
