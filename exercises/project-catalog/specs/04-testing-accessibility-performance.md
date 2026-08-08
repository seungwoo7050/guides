# Stage 04 — 접근성·반응형·성능 예산

## 사용자 결과

사용자는 keyboard만으로 검색과 편집을 완료한다. editor를 취소하거나 성공적으로 저장하면 시작 button으로 focus가 복구된다. conflict와 일반 실패에서는 draft와 input focus가 유지된다. 작은 화면과 확대에서도 작업할 수 있다.

## 구현할 것

### Focus와 의미 구조

- main, heading, search form, label, list와 article을 의미에 맞게 사용한다.
- loading·failure·save 결과를 live region으로 알린다.
- editor open 시 title input에 focus한다.
- 취소와 성공 뒤 해당 project의 edit button으로 focus를 돌린다.
- 일반 실패와 conflict에서는 editor와 draft, input focus를 유지한다.
- 눈에 보이는 `:focus-visible` 표시를 제공한다.

### Responsive와 motion

- 320px에서 horizontal page overflow를 만들지 않는다.
- 200% 확대에서도 주요 control이 잘리지 않는다.
- 공백 없는 80자 title이 article을 넘지 않는다.
- form control과 grid child의 최소 폭을 안전하게 만든다.
- `prefers-reduced-motion`에서 transition·animation을 사실상 제거한다.

### 성능 예산

`performance-budget.json`의 다음 두 값을 넘지 않는다.

- 첫 route가 요청한 JavaScript response body byte 합계
- 첫 화면의 DOM element 수

`TODO(stage-04)` 표시를 모두 제거한다.

## 완료 조건

```sh
pnpm exercise:verify:04
```

Stage 01–04 unit test, production build와 `@stage-03`, `@stage-04` browser test가 모두 통과해야 한다.
