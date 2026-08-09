# Meta 탐지 계획

## Event Schema
검사 시작, 파일 판정, 오류와 종료 코드를 구조화해 기록합니다.

## Identity Chain
로컬 사용자에서 Python process와 fixture path로 이어지는 실행 문맥을 기록합니다.

## 탐지 가설
DET-001은 incomplete fixture acceptance, DET-002는 valid fixture rejection을 탐지합니다.

## 분석 규칙
예상 종료 코드와 실제 종료 코드가 다르면 meta-test를 실패시킵니다.

## Known-positive와 Known-negative Fixture
invalid는 positive이고 valid는 negative이며 두 결과를 고정합니다.

## Triage와 Containment
실패한 field와 fixture를 확인하고 release를 차단합니다.

## Pipeline Health
세 fixture가 모두 실행됐는지와 Python exception을 확인합니다.
