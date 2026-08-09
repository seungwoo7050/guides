# 사이버보안 프로젝트 진입 지도

이 가이드 뒤에는 분야를 다시 처음부터 공부하기보다 실제 코드와 운영 자료에서 작은 문제를 반복해 해결합니다.

## 공통 진입 순서

```text
프로젝트 scope와 기여 정책 확인
→ build·test·security policy 실행
→ 최근 security issue와 수정 이력 조사
→ 작은 실패를 재현
→ test·fixture·문서부터 개선
→ root cause patch
→ 재검증과 운영 근거
→ 같은 하위 시스템에 반복 기여
```

## 역할별 첫 기여

### Application·Product Security

- authorization regression test
- parser·upload·path 처리의 known-bad fixture
- threat model의 data flow·identity 누락 보완
- security requirement와 review checklist
- 취약점 report의 재현·root cause·retest 개선

### Security Engineering

- secure default와 configuration validation
- credential scope·rotation·audit 개선
- sandbox·policy enforcement test
- artifact identity·SBOM·provenance 검증
- 보안 검토와 exception lifecycle 자동화

### Vulnerability Analysis

- scanner false-positive 최소 fixture
- crash·fuzz input 최소화
- source-to-runtime reachability 분석
- advisory 영향 범위와 patch verification
- 안전한 coordinated disclosure 문서

고급 exploit 개발은 별도 전문 훈련과 엄격한 허가 환경이 필요합니다.

### Detection·Response

- event schema와 actor·resource correlation
- detection rule의 known-positive·negative fixture
- pipeline health와 stale-data alert
- incident timeline과 evidence collection 개선
- recovery validation과 tabletop exercise

### Open Source Supply Chain

- dependency policy와 lockfile·artifact 검증
- release provenance·signature 확인
- build isolation과 CI credential 최소화
- package namespace·mirror 경계 test
- compromise 후 trusted rebuild 절차

## 첫 issue 선택 기준

- 범위가 한 module·policy·event type으로 제한됩니다.
- 재현 가능한 합성 fixture를 만들 수 있습니다.
- 실제 사용자 data와 외부 target이 필요하지 않습니다.
- 결과를 test·log·artifact로 확인할 수 있습니다.
- maintainer가 수정 방향을 논의할 수 있습니다.

## 피해야 할 시작점

- 승인 없이 “전체 보안 감사”를 수행함
- scanner 출력 수백 건을 issue로 일괄 등록함
- production configuration을 직접 시험함
- security boundary 전체를 한 PR에서 재설계함
- 공개 전 상세 exploit을 먼저 게시함
- 실제 incident에서 사실과 추측을 섞어 기여함

## 깊이를 만드는 반복

한 번의 취약점 발견보다 같은 boundary에서 다음을 반복하는 편이 중요합니다.

```text
설계 invariant
→ implementation
→ regression
→ runtime evidence
→ incident feedback
→ invariant 개선
```

이를 통해 단일 finding 해결에서 하위 시스템의 보안 소유로 이동합니다.

## 카탈로그의 다음 경로

`main` 카탈로그에서 이 브랜치의 직접 `continues_to`는 `platform-engineering`입니다. 여러 팀이 사용하는 보안 정책·CI/CD·관측·복구 경로를 self-service 제품으로 만들려면 그 브랜치로 이어갑니다. 이때 이 브랜치가 만드는 것은 공격 가설과 검증 evidence이고, 플랫폼 브랜치가 소유하는 것은 다팀 실행 경로와 운영 수명 주기입니다.

직접 `connects`는 다음 두 전문 영역도 포함합니다.

- `agentic-systems`: 도구 권한, 외부 입력, 장기 실행 state와 verifier 경계를 다룰 때 연결합니다. agent 구현과 평가 체계 자체는 해당 브랜치가 소유합니다.
- `embedded-systems`: firmware update, debug capability, device identity와 물리 경계를 다룰 때 연결합니다. MCU·RTOS·driver 구현은 해당 브랜치가 소유합니다.

현재 카탈로그 안에 고급 exploit 연구·전문 DFIR·GRC 전 과정을 소유하는 후속 브랜치는 없습니다. 그런 업무는 조직의 명시적 허가, 법무·privacy·risk acceptance 절차와 별도 전문 교육을 통해 확장합니다.
