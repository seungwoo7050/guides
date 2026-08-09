# 누적 실습: Modern-model transfer와 release

작은 로컬 sequence fixture와 고정된 toy base encoder로 tokenizer 계약, causal attention, frozen feature와 partial fine-tuning 비교, 재현 가능한 release bundle을 네 단계에 걸쳐 완성한다. 외부 model download, 네트워크, GPU와 제3자 package가 필요 없다. 이 축소 모델의 점수는 실제 foundation model 성능을 대표하지 않는다.

## 학습 결과

```text
tokenizer/base version 계약
→ attention shape·mask·softmax 불변식
→ frozen head와 partial adapter를 validation에서 비교
→ base regression + bundle + golden inference + model card + release review
```

점수보다 경계가 중요하다. Test label은 선택에 영향을 주면 안 되고, adapter는 base와 tokenizer의 ID·version·digest 없이는 release unit이 아니다.

## 제공 구조

```text
contracts/stages.json       4단계 산출물 계약
fixtures/                   synthetic sequence, tokenizer, base, regression case
skeleton/                   의도적으로 미완성인 학습자 시작점
reference/                  표준 라이브러리 CPU 완성 경로
known_bad/                  한 불변식씩 깨뜨린 6개 negative control
tests/check.py              공개 행동 검사기
```

Fixture와 checker는 직접 고치지 않는다. 작업하려면 `skeleton/`을 저장소 밖 또는 별도 `workspace/`로 복사한다.

## 공개 candidate 계약

후보 루트의 `candidate.py`는 세 명령을 제공한다.

```sh
python3 candidate.py attention --base BASE.json --tokens 1,2,3
python3 candidate.py build --fixtures FIXTURES --output EMPTY_DIR
python3 candidate.py infer --bundle BUNDLE --input INPUT.json
```

`attention`은 JSON `weights`와 `context`를 출력한다. `build`는 기존 결과를 덮어쓰지 않고 네 단계 산출물을 만든다. `infer`는 정확히 `{"text": "..."}` 입력만 받고 `model_version`, `probability`, `decision`을 출력한다. Missing field, 추가 field, 비문자열, 빈 sequence, unknown token과 최대 길이 초과는 비정상 종료한다.

Reference bundle은 clean process에서도 같은 계약을 제공한다.

```sh
modern_output=$(mktemp -d /tmp/modern-model-reference.XXXXXX)
python3 reference/candidate.py build --fixtures fixtures --output "$modern_output"
PYTHONPATH=reference/src python3 -m model_project.inference \
  --bundle "$modern_output/artifacts/bundle" \
  --input "$modern_output/artifacts/bundle/golden-input.json"
```

명령은 새 임시 output에만 쓴다. 결과 확인 뒤 필요하지 않으면 출력된
`modern_output` 경로만 정리하고 `fixtures/`나 candidate source는 지우지 않는다.

## 1단계: Tokenizer와 base 계약

`fixtures/tokenizer.json`과 `fixtures/base-model.json`을 읽고 다음을 `reports/01-tokenizer-contract.json`에 기록한다.

- tokenizer와 base의 ID·version·SHA-256
- normalization, vocabulary와 max length
- unknown token을 거부하는 정책
- base가 요구하는 tokenizer ID·version·길이의 일치

Token ID를 바꾸거나 unknown을 padding으로 처리하면 base embedding의 의미가 달라진다. Version 문자열만 같고 bytes가 다를 때도 digest가 차이를 드러내야 한다.

## 2단계: Attention 불변식

세 token probe에서 `[sequence, sequence]` weight와 `[sequence, hidden]` context를 관찰한다.

- 각 query row는 허용된 key 방향으로 softmax되어 합이 1이다.
- causal query `i`의 `j > i` weight는 정확히 0이다.
- mask는 softmax 전에 적용된다.
- 고정 base regression case가 tolerance 안에서 재현된다.

결과와 검사한 shape·axis·최대 future weight를 `reports/02-attention-invariants.json`에 남긴다. `known_bad/causal-mask-reversal`과 `known_bad/wrong-softmax-axis`가 왜 거부되는지 설명할 수 있어야 한다.

## 3단계: Frozen과 partial transfer

Train에서만 head/adapter를 fit하고 validation log loss로 mode와 epoch를 선택한다.

1. Base를 고정한 feature 위에 작은 logistic head를 학습한다.
2. Base embedding은 고정한 채 element-wise adapter와 head 일부만 학습한다.
3. 같은 split, initialization·metric 계약에서 비교한다.
4. 선택 뒤 test를 한 번 평가한다.
5. Base regression을 다시 실행해 base가 변하지 않았음을 확인한다.

`reports/03-transfer-comparison.json`에는 split count, 두 trace, selection split, 선택 mode/epoch, test 1회 결과와 base identity를 포함한다. Checker는 test label을 뒤집어도 adapter bytes가 바뀌지 않는지 확인한다.

## 4단계: Release unit

`artifacts/bundle/`에 다음을 함께 묶는다.

```text
manifest.json
base-model.json
tokenizer.json
adapter.json
model-card.md
golden-input.json
golden-output.json
```

Manifest는 결합되는 base·tokenizer identity, 모든 파일 digest, 입출력 계약과 threshold를 가진다. Adapter에도 같은 base·tokenizer identity가 있어야 한다. `reports/04-release-review.md`는 decision, evidence, blocker, control, revalidation 조건을 구분한다.

## 검사

Reference는 통과해야 한다.

```sh
python3 tests/check.py --candidate reference
```

Starter와 known-bad는 거부돼야 한다.

```sh
python3 tests/check.py --candidate skeleton
for candidate in known_bad/*/; do
  python3 tests/check.py --candidate "$candidate"
done
```

검사기는 causal mask·softmax axis, base regression, validation-only selection, test-label 독립성, exact artifact identity·digest, golden parity와 invalid-input rejection을 관찰한다. 실제 데이터 대표성, 외부 pretrained model의 license·공급망, 대규모 GPU 수치 안정성과 운영 안전은 자동 증명하지 않는다.

## 자원·안전·복구

- Reference는 작은 JSON fixture와 Python 표준 라이브러리만 사용하며 CPU에서 수 초 안에 끝나는 것이 목표다.
- 실제 고객 data, credential, 외부 model weight를 이 디렉터리에 넣지 않는다.
- Candidate output은 새 빈 디렉터리에만 만든다. 작업 결과가 필요 없으면 그 별도 output만 제거하며 fixture/source는 삭제하지 않는다.
- 외부 모델로 확장할 때는 license, tokenizer·weight digest, remote-code 실행, memory/시간 한도와 rollback을 별도로 검토한다.

관련 개념은 [`tokenization`](../../docs/05-modern-models/01-embeddings-and-tokenization.md), [`attention`](../../docs/05-modern-models/02-attention-and-transformers.md), [`transfer와 fine-tuning`](../../docs/05-modern-models/03-pretraining-transfer-and-fine-tuning.md), [`artifact`](../../docs/06-model-lifecycle/01-experiments-reproducibility-and-artifacts.md), [`inference 계약`](../../docs/06-model-lifecycle/02-inference-contracts-and-delivery.md)을 먼저 읽는다.
