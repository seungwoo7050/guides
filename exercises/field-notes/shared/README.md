# Field Notes shared contract

`@field-notes/shared`는 skeleton과 reference가 같은 업무 언어를 사용하도록 하는 순수 TypeScript package다.

- `contracts.ts`: record, permission/availability, navigation intent와 Stage 01 판정 type
- `ports.ts`: 이후 Stage에서 구현할 repository·file·session·sync·device·background 경계
- `fixtures.ts`: Stage 01 process memory에서만 사용하는 세 기록
- `testkit.ts`: framework에 독립적인 정상·경계·실패 사례와 contract evaluator

이 package에는 parser나 storage 정답 구현이 없다. skeleton과 reference의 구현을 같은 행동 사례로 대조하기 위한 경계다.

