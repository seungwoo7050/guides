# Model lifecycle workspace

이 디렉터리는 `scripts/new-workspace.sh`가 복사하는 학습자 출발점이다.

## 입력

직접 수정하지 않는 공용 입력은 workspace의 상위 디렉터리에 있다.

```text
../fixtures/
../templates/
../contracts/
```

## 권장 구조

```text
src/model_project/       dataset·model·evaluation 코드
tests/                   자신의 단위·통합 검사
reports/                 단계별 Markdown·JSON·JSONL
artifacts/model-bundle/  release candidate bundle
```

## 구현 프로필

- 표준 라이브러리만 사용해 1~3·5·7·8단계 문서와 기준 metric을 만들 수 있다.
- scikit-learn을 사용하면 4단계의 preprocessing·classical model을 빠르게 구현할 수 있다.
- PyTorch를 사용하면 6단계 training loop를 구현할 수 있다.
- 직접 구현을 선택해도 되지만 numerical stability와 test 책임은 학습자에게 있다.

외부 package는 workspace의 별도 virtual environment에 설치한다. 저장소의 검증 환경이 이를 자동 설치하지 않는다.

## 검사

저장소 루트에서 현재 단계까지 구조를 확인한다.

```sh
python3 scripts/check-submission.py \
  --workspace exercises/model-lifecycle/workspace \
  --stage 1
```

이 검사는 model quality를 판정하지 않는다. 자신의 test와 review report를 함께 만든다.
