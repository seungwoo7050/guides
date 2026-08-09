# Fixture provenance and limits

`sequences.jsonl`, `tokenizer.json`, `base-model.json`과 `base-regression.json`은 이 가이드를 위해 손으로 만든 synthetic 교육 자료다. 사람·고객·운영 기록이나 외부 model weight를 포함하지 않는다.

- `train`, `validation`, `test` ID는 서로 겹치지 않는다.
- Label `1`은 이 toy task의 `escalate` decision만 뜻한다.
- Base embedding과 vocabulary는 실제 언어 의미·안전·공정성을 대표하지 않는다.
- Fixture를 바꾼 결과는 기존 reference 주장과 비교할 수 없으므로 별도 version으로 취급한다.

실제 dataset이나 pretrained artifact로 확장할 때는 provenance, license, privacy, contamination, tokenizer/weight digest와 remote-code 신뢰 경계를 새로 검토해야 한다.
