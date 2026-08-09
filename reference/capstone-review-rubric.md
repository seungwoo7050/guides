# Capstone review rubric

각 항목을 `미충족`, `부분`, `충족`, `강함`으로 평가합니다.

## 1. 에이전트 자체 개발

- 기존 agent SDK를 호출하는 wrapper가 아니라 runtime 핵심을 소유합니다.
- model adapter를 교체할 수 있습니다.
- scripted model로 runtime을 결정적으로 검사합니다.

## 2. 저장소 이해

- Git baseline과 instruction/environment discovery가 있습니다.
- target file을 사전에 고정하지 않습니다.
- source·test·config·command를 evidence로 연결합니다.

## 3. 도구와 실행

- safe filesystem, multi-file patch, process runner와 Git adapter가 있습니다.
- timeout·cancel·child cleanup·output limit을 다룹니다.
- receipt와 actual diff가 일치합니다.

## 4. 코딩 loop

- 재현·가설·plan·edit·test·repair가 있습니다.
- 첫 실패 뒤 evidence 기반으로 재계획합니다.
- 좁은 검사와 넓은 검사를 구분합니다.

## 5. 안전과 사용자 통제

- prompt injection과 malicious repository case가 있습니다.
- permission·approval·sandbox가 prompt 밖에서 강제됩니다.
- 질문·승인·cancel·resume·final review가 있습니다.

## 6. 평가

- fixture와 external hidden verifier가 분리됩니다.
- known-bad patch를 거절합니다.
- evaluation error를 agent failure와 구분합니다.
- trace·cost·user intervention을 보고합니다.

## 게시 전 필수

다음 중 하나라도 없으면 Capstone 완료로 표시하지 않습니다.

- 다중 파일 변경
- 실제 command/test 실행
- 실패 뒤 repair iteration
- external verifier
- repository prompt injection 또는 권한 실패 case
