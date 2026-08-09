# Meta 위협 모델

## 시스템 경계
로컬 verifier와 fixture 사이가 검사 경계입니다.

## 자산
검사 결과의 무결성과 false acceptance 방지가 자산입니다.

## 행위자와 Capability
학습자는 파일을 편집하고 verifier는 읽기 전용으로 판정합니다.

## 신뢰 경계와 흐름
fixture가 parser로 들어가 validation 결과가 반환됩니다.

## 위협
THR-001 필수 파일 누락, THR-002 근거 없는 finding, THR-003 trace 누락을 검토합니다.

## 공격 경로
THR-001에서 불완전 자료가 통과하면 잘못된 완료 판정으로 이어집니다.

## Choke Point와 우회 경로
필수 schema와 cross-file trace가 공통 차단 지점이며 문구 복사는 우회가 될 수 있습니다.

## 가정과 미확인
기술적 판단의 정확성은 구조 검사만으로 판정하지 못합니다.
