# Capstone D: Modern-model transfer release

이 capstone은 pretrained artifact를 호출하는 데서 끝나지 않고 **tokenizer·base·adapter·evaluation·inference를 하나의 검토 가능한 release unit으로 만드는 능력**을 평가한다. 실행 기반은 [`modern-model-release` 누적 실습](../../exercises/modern-model-release/README.md)이다.

## 목표

다음 연결을 실행 결과와 문서로 입증한다.

```text
tokenizer/version
→ causal attention 불변식
→ frozen 대 partial transfer 선택
→ base capability regression
→ exact bundle identity
→ golden inference와 release decision
```

## 수행 조건

- 제공된 작은 synthetic sequence와 base artifact를 사용한다.
- Train으로만 fit하고 validation으로 mode·epoch를 선택한다.
- Test는 선택이 끝난 뒤 한 번만 평가한다.
- Base parameter는 수정하지 않고 regression case를 전후에 비교한다.
- Unknown·malformed input을 조용히 coercion하지 않는다.
- Network, GPU와 유료 자원은 사용하지 않는다.

## 필수 증거

| 주장 | 증거 |
|---|---|
| tokenizer가 base와 호환됨 | ID·version·digest와 max-length 계약 |
| causal attention이 올바름 | shape, query별 row sum, future-weight zero probe |
| transfer 선택이 독립적임 | frozen/partial trace, validation 선택, test-label mutation |
| base capability가 보존됨 | 고정 regression case와 불변 base digest |
| release를 재현할 수 있음 | base+tokenizer+adapter manifest, file digest, model card |
| inference 계약이 명확함 | clean-process golden parity와 invalid-input failure |

## 실패 분석

다음 여섯 failure를 checker 결과와 연결해 설명한다.

1. Causal mask 방향 반전
2. Key가 아닌 query 방향 softmax
3. Tokenizer/base version 불일치
4. Test 기반 mode 또는 epoch 선택
5. Adapter에 base identity 누락
6. 잘못된 입력의 암묵적 coercion

각 항목에 증상, 위반한 불변식, release 영향, 수정 뒤 재검사를 기록한다.

## Release review

최종 결정은 `APPROVE FOR EXERCISE ONLY`, `DEFER`, `REJECT` 중 하나로 제한한다. Synthetic fixture 통과를 실제 제품 승인으로 확대 해석하지 않는다. Review에는 다음을 포함한다.

- 검토한 base·tokenizer·adapter·schema·threshold version
- 지원되는 주장과 지원되지 않는 주장
- blocker와 non-blocker
- input rejection, artifact immutability와 rollback control
- base/tokenizer/data/runtime 변경 시 재평가 범위

## 완료 기준

- [ ] 4단계 산출물이 모두 실제 실행 결과에서 생성됐다.
- [ ] Reference checker가 후보를 통과시킨다.
- [ ] Test label 변경이 선택 model/parameter를 바꾸지 않는다.
- [ ] 여섯 known-bad 후보가 각 공개 불변식에서 거부된다.
- [ ] Bundle digest와 adapter의 base/tokenizer identity가 일치한다.
- [ ] Golden inference가 clean process에서 재현된다.
- [ ] Missing·extra·wrong-type·unknown·too-long input이 실패한다.
- [ ] Model card가 intended use, 평가, limitation과 identity를 설명한다.
- [ ] 자동 검사로 판단할 수 없는 실제 data·license·GPU·운영 한계를 명시한다.

완료 결과는 높은 정확도 자체가 아니라, transfer 선택과 release 주장을 독립된 증거로 추적하고 실패를 안전하게 거부하는 능력으로 판단한다.
