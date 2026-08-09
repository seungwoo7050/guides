# Fixture schema 원칙

이 저장소의 JSON·CSV fixture는 production wire format이 아니다. 학습자가 상태와 교차 참조를 읽고 실패를 분석할 수 있도록 만든 합성 입력이다.

## 공통 규칙

- 모든 id는 파일 안에서 유일하고 의미가 안정적이어야 한다.
- 사건 배열은 `index`, `sequence`, `tick` 중 필요한 ordering field를 가진다.
- 상태와 event를 같은 object로 표현하지 않는다.
- `null`, `unknown`, `missing`을 서로 다른 의미로 사용한다.
- 숫자의 단위를 field 이름에 포함한다. 예: `frame_ms`, `fixed_step_us`, `memory_mib`.
- build, content, save, replay와 protocol identity를 분리한다.
- 실제 개인·계정·서버·secret 데이터를 포함하지 않는다.

## JSON fixture

- UTF-8, object 또는 array를 사용한다.
- map iteration order에 의미를 두지 않는다.
- ordered event는 배열과 명시적 sequence/tick을 사용한다.
- stable id reference는 같은 fixture set에서 resolve 가능해야 한다.
- known-bad input은 무엇이 잘못됐는지 README에 설명한다.

## CSV fixture

- 첫 줄은 비어 있지 않은 header다.
- row마다 같은 column 수를 유지한다.
- 여러 값을 한 cell에 숨기기보다 별도 row 또는 JSON을 고려한다.
- template의 빈 cell은 학습자가 채울 자리이며 input fixture의 누락과 다르다.

## 변경 시 검사

```sh
make fixtures
```

검사는 JSON parse, CSV shape, duplicate id, manifest dependency와 요구사항 참조를 확인한다. 자동 검사가 의미적 정답을 보장하지 않으므로 변경자는 다음도 검토한다.

- 실패가 실제로 학습 목표와 연결되는가?
- 의도하지 않은 두 번째 해법/우회가 생겼는가?
- 문서의 설명과 field 이름·단위가 일치하는가?
- known-bad fixture가 checker 또는 설계 검토에서 실제로 거부되는가?
