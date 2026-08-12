# 사고 대응 기록

겹쳐 나타난 배포·502·DB connection·disk 증상에서 사실과 가설을 분리하고 안전한 대응 순서를 작성합니다.

관련 문서: [`docs/17-incident-response-and-runbooks.md`](../../docs/17-incident-response-and-runbooks.md)

## 입력

```text
fixtures/incident.json
```

에는 관측 event와 운영자 제안이 시간순으로 들어 있습니다.

## 작성 대상

```text
workspace/response.yaml
```

다음을 완성합니다.

- 사용자 영향 기반 severity
- incident commander·operations·communications·scribe
- 변경 동결
- 증거가 있는 observation
- 검증 가능한 hypothesis
- 가역적인 초기 조치
- 증거를 지우는 위험한 명령의 거부
- 완화와 근본 수정의 분리
- 외부 기능과 데이터 상태를 포함한 복구 검증
- owner·기한·검증 방법이 있는 후속 작업

## 검증

```sh
python3 scripts/new-workspace.py exercises/17-incident-response
cd exercises/17-incident-response
./verify.sh workspace
```

작업공간 생성 명령은 저장소 루트에서 실행합니다. 정답 원인 하나를 맞히는 문제가 아닙니다. 불확실한 상황에서 피해와 정보 손실을 키우지 않는 순서를 검증합니다. 자기 설명까지 마친 뒤에만 `reference/response.yaml`을 expected evidence 예시로 읽고 `./verify.sh reference`와 비교합니다.

## 권장 작성 순서

`reference/response.yaml`은 code 구현이 아니라 가능한 expected evidence 한 가지입니다. 아래 번호는 실제 Git 이력이 아닌 학습용 작성 순서이며 YAML에 comment 표식을 강제하지 않습니다.

| 번호 | 작성 경계 |
|---:|---|
| [Implementation 1] | 사용자 impact·severity·roles·change freeze |
| [Implementation 2] | observation과 입력 event fact 분리 |
| [Implementation 3] | falsifiable hypothesis와 확인 방법 |
| [Implementation 4] | 가역적 initial action과 destructive proposal 거부 |
| [Implementation 5] | mitigation·external path·data recovery verification |
| [Implementation 6] | 불확실성을 보존하는 communication |
| [Implementation 7] | owner·deadline·verification이 있는 follow-up |

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 모든 observation은 입력 event 증거를, 모든 hypothesis는 반증 가능한 확인 방법을 가진다.
- [ ] 역할과 변경 동결을 먼저 세우고 증거를 보존하는 가역 조치, 완화, 근본 수정을 서로 다른 단계로 기록한다.
- [ ] 복구 확인에 외부 사용자 기능과 데이터 상태가 포함되고 후속 작업마다 owner·기한·검증 방법이 있다.

## 자기 설명

1. incident 초기에 원인 단정 대신 사실과 가설을 분리하면 어떤 잘못된 조치를 피할 수 있는가?
2. 로그 삭제나 즉시 재생성보다 가역적인 부하 완화와 증거 보존을 먼저 해야 하는 이유는 무엇인가?
3. 사용자 영향 severity와 기술 구성요소 오류의 심각도가 항상 같지 않은 이유는 무엇인가?
