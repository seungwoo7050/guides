# 기여 가이드

## 목적

이 브랜치는 게임 엔진 API 목록이 아니라 게임 프로젝트의 **상태·시간·수명·콘텐츠·실패·검증 계약**을 가르친다. 변경은 특정 엔진의 편의 기능을 소개하는 데서 끝나지 않고 다른 프로젝트에도 남는 판단 기준을 제공해야 한다.

## 변경 전 확인

1. 같은 개념의 정본이 다른 브랜치에 있는지 확인한다.
2. 현재 변경이 게임 고유의 적용 차이인지 설명한다.
3. 정상 사례 외에 경계·실패·복구를 포함한다.
4. 성능·결정성·호환성 주장은 범위와 재현 명령을 붙인다.
5. 실제 사용자/서비스 데이터, 비밀값과 무단 대상은 fixture에 넣지 않는다.

## 문서 형식

`docs/01`~`docs/16`의 개념 문서는 다음 절을 유지한다.

```text
## 문제
## 핵심 상태
## 설계 계약
## 대표 실패
## 관찰과 검증
## 실습 연결
## 기존 브랜치와 경계
## 완료 기준
```

모든 절의 길이를 같게 만들 필요는 없지만, 도구 사용법만 있고 상태·실패·검증이 없는 문서는 추가하지 않는다.

## 용어와 문체

- 엔진별 class/API는 예시로만 사용하고 일반 개념과 분리한다.
- “항상”, “완전 결정적”, “server authoritative”, “60 FPS 보장” 같은 표현은 범위를 함께 쓴다.
- frame과 tick, entity와 asset, stable id와 runtime handle, save와 replay를 혼용하지 않는다.
- 의도·팀의 판단을 추측하지 않고 코드·fixture·공식 문서에서 확인한 사실과 제안을 구분한다.
- 한국어 설명 안에서 필요한 기술 용어는 원문을 유지하되 같은 개념에 여러 표기를 무작위로 섞지 않는다.

## 실습 변경

실습은 다음을 포함한다.

- 합성 system brief 또는 fixture
- 의도적으로 미완성인 학습자 template/starter
- fixture가 결정하는 결과의 완성 reference 또는 expected evidence
- 대표 오답
- 사람 검토 질문
- 완료 기준

설계 문구를 하나의 정답으로 강제하지 않는다. 다만 시간 계산, 상태 전이, command trace, schema migration, percentile, release gate처럼 입력으로 결정 가능한 결과에는 완성 reference/expected evidence가 필요하다. 자동 검사는 CSV/JSON 관측값과 공개 불변식을 읽고, 사람 판단은 `MANUAL_REVIEW_REQUIRED` 질문과 필요한 증거로 분리한다.

검사기는 같은 공개 계약으로 다음 세 방향을 확인해야 한다.

1. 완성 reference는 통과한다.
2. 미완성 template/starter는 거부된다.
3. 최소 한 개의 대표 behavioral mutant는 거부된다.

source 문자열이나 특정 문장 일치를 학습 완료의 대리 지표로 사용하지 않는다. 검증 과정은 추적 fixture/template, reference와 학습자 workspace를 덮어쓰거나 삭제하지 않아야 한다.

fixture를 변경하면 다음을 실행한다.

```sh
make fixtures
make example
make meta
./verify.sh
```

known-bad case를 제거하거나 checker가 거짓 성공하도록 바꾸지 않는다.

## 학습용 Implementation annotation

- `examples/fixed-step-replay` 전체와 `projects/relay-arena-vertical-slice/reference` 전체가 각각 하나의 numbering scope다. 파일마다 번호를 다시 시작하지 않는다.
- 번호는 Git history나 runtime call order가 아니라 README에 선언한 학습용 권장 구현 순서다.
- exact `[Implementation N]` 또는 `[Implementation N-M]` anchor는 scope 안에서 한 번만 사용하고 top-level·child 번호를 각각 1부터 연속시킨다.
- source anchor가 있는 단계는 README index에서 bracket 없는 번호를 사용한다. JSON처럼 주석을 허용하지 않는 artifact만 owning README 표가 exact sidecar anchor를 소유한다.
- skeleton, template, starter, tests, fixtures, expected oracle, known-bad, scripts와 prepare/verify infrastructure에는 annotation을 넣지 않는다.
- 이 브랜치의 두 scope에는 project/dependency/framework bootstrap이 없으므로 Implementation 0이 없다. workspace 복사, build, run과 verification을 0으로 만들지 않는다.
- annotation 때문에 public CLI, JSON output, state hash, exit status와 mutant rejection을 바꾸지 않는다.

## 안전·생성물·커밋 범위

- 실제 사용자·production 데이터, API key, token, cookie와 credential-bearing 설정을 fixture나 로그에 넣지 않는다.
- 기본 검사는 Python 3.10 표준 라이브러리와 합성 fixture만 사용하며 유료 자원, 실제 배포나 외부 시스템 변경을 요구하지 않는다.
- 학습자 작업은 `scripts/new-workspace.sh`로 저장소 밖 새 경로에 만들고 기존 경로·symlink를 덮어쓰지 않는다.
- `.guide/`, cache, log, build·dist·out과 editor 개인 설정을 커밋하지 않는다.
- `make clean`의 범위를 marker와 Python cache보다 넓히지 않는다. 학습자 workspace나 명시되지 않은 실행 결과는 정리 대상이 아니다.
- commit 전 `git diff --check`, source/secret/generated-file audit와 관련 검사를 실행하고 의미 단위의 확인된 경로만 stage한다.

세부 규칙은 [안전·환경·증거 계약](reference/safety-and-environment.md)을 따른다.

## 외부 자료

- 공식 엔진·플랫폼·표준 문서를 우선한다.
- 링크와 확인 날짜는 `docs/90-engine-and-source-map.md`에 모은다.
- 외부 문장·코드·그림을 무단 복사하지 않는다.
- 문서와 코드의 라이선스는 [`LICENSE.md`](LICENSE.md)를 따른다.

## Pull Request 설명

다음을 포함한다.

```text
문제와 대상 독자
현재 소유 범위와 중복 여부
변경한 상태·실패·검증 계약
추가/수정한 fixture와 known-bad case
실행한 검사
남은 한계와 후속 브랜치
```
