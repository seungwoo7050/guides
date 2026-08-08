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
skeleton/response.yaml
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
cd exercises/17-incident-response
./verify.sh skeleton
./verify.sh reference
```

정답 원인 하나를 맞히는 문제가 아닙니다. 불확실한 상황에서 피해와 정보 손실을 키우지 않는 순서를 검증합니다.
