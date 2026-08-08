# 애플리케이션 경계 실습

## 목표

설정 binding, HTTP 입력 검증과 업무 정책을 서로 다른 경계에 배치한다. 범위를 벗어난 요청은 RFC 9457 `ProblemDetail`로 번역하고, 서로 모순되는 설정은 첫 요청 전 Context 시작 단계에서 거부한다.

## 완료 기준

- 최소값보다 작은 요청과 최대값보다 큰 요청이 모두 `POLICY_VIOLATION`으로 거부된다.
- 비어 있거나 형식이 잘못된 본문은 controller 업무 코드에 도달하기 전에 400이 된다.
- `minimum > maximum` 설정으로 Context를 시작하면 원인을 포함한 검증 오류로 실패한다.

## 자기 설명

- Bean Validation과 업무 범위 검사를 같은 annotation 하나로 합치면 어떤 변경에 취약한가?
- 잘못된 설정을 첫 요청이 아니라 시작 단계에서 거부해야 하는 운영상 이유는 무엇인가?

## 검증

canonical skeleton의 `PreviewController`는 최대 경계를 빠뜨린 고정 실패 fixture다. tracked skeleton은 수정하지 않고 학습자 workspace에서 양쪽 경계를 구현한다.

```sh
./scripts/new-workspace.sh application-boundaries
#학습 구현: .workspace/application-boundaries/src/main을 수정한다.
./scripts/check-workspace.sh application-boundaries
./scripts/mvn-guide.sh -pl :application-boundaries-reference -am test
```
