# 사이버보안 분석·검증·대응 로드맵

사이버보안에서 공격과 방어는 서로 다른 현실을 다루는 두 과정이 아닙니다. 공격 관점은 **보안 주장이 실제 실패 조건을 견디는지 검증하는 방법**이고, 방어 관점은 **그 실패를 예방·탐지·복구하도록 시스템 계약을 바꾸는 작업**입니다.

이 가이드는 다음 흐름을 하나의 개발 작업으로 연결합니다.

```text
보호할 상태
→ 공격 전제와 신뢰 경계
→ 허가된 검증
→ finding과 영향
→ 원인 수정
→ 회귀와 hardening
→ 탐지와 대응
→ 잔여 위험 결정
```

## 학습 목표

- 보안을 “도구 설치”가 아니라 시스템 상태와 증거의 문제로 다룹니다.
- 개별 취약점보다 권한·신뢰·데이터 흐름이 연결된 공격 경로를 분석합니다.
- 공격 결과를 수정·회귀·탐지·복구 계약으로 되돌립니다.
- 실제 보안 프로젝트와 오픈소스에 합류할 수 있는 문서·검증 산출물을 만듭니다.

## 종료 능력

가이드를 마친 독자는 다음을 수행할 수 있어야 합니다.

1. 시스템 context와 asset register에서 보호할 상태와 신뢰 경계를 찾습니다.
2. 행위자의 능력, 진입점, precondition과 postcondition으로 위협을 작성합니다.
3. scope, Rules of Engagement, stop condition과 evidence handling을 포함한 평가 계획을 만듭니다.
4. 자동 도구가 제시한 후보를 최소 재현과 독립 증거로 검증합니다.
5. 애플리케이션·시스템·identity·secret·공급망의 약점을 하나의 attack path로 연결합니다.
6. finding을 검증 상태별 근거로 보고하고, confirmed 항목에는 인과적으로 지지된 root cause·severity와 적용되는 remediation을 연결합니다.
7. 위협을 보안 requirement와 부정 테스트로 변환합니다.
8. 패치 뒤 credential rotation, data cleanup, regression과 재검증 범위를 결정합니다.
9. event schema와 detection hypothesis를 작성하고 alert의 false positive·false negative를 평가합니다.
10. incident timeline에서 사실·가설·결정과 복구 증거를 분리합니다.
11. release 전에 미해결 finding, compensating control, evidence age와 risk owner를 검토합니다.
12. 실제 프로젝트에서 문서·테스트·재현·작은 패치부터 기여를 시작합니다.

## 대상 독자

다음 중 하나에 해당하면 시작할 수 있습니다.

- 웹·백엔드·시스템·인프라 개발 경험이 있고 보안 변경을 제대로 검토하고 싶습니다.
- 취약점 보고를 읽을 수 있지만 실제 영향과 수정 검증을 연결하기 어렵습니다.
- 보안 도구의 결과를 해석하고 false positive를 구분하고 싶습니다.
- AppSec, Product Security, Security Engineering, Detection/Response 또는 취약점 연구 프로젝트의 진입점을 원합니다.

이 가이드는 프로그래밍을 처음 배우는 과정이 아닙니다. 최소한 파일을 읽고 명령을 실행하며 JSON과 Markdown을 수정할 수 있어야 합니다.

## 선행 가이드와 경계

### 필수에 가까운 기반

| 기반 | 필요한 종료 능력 |
|---|---|
| [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) | 파일·권한·프로세스·socket·service 상태를 읽기 전용 근거로 조사합니다. |
| [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) | DNS·IP·transport·TLS·HTTP 실패를 다른 계층으로 분리합니다. |

두 브랜치를 반드시 처음부터 다시 완료할 필요는 없습니다. 위 종료 능력이 없다면 관련 문서를 먼저 보완합니다.

### 문제에 따라 선택할 기반

| 상황 | 연결할 가이드 |
|---|---|
| 웹 권한·session·입력 경계 | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) |
| 공개 host·release·secret·backup·incident | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) |
| process isolation·memory·race·filesystem | [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) |
| C memory bug·sanitizer·POSIX API | [`c`](https://github.com/seungwoo7050/guides/tree/c) |
| CPU·memory hierarchy·privilege 기초 | [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) |
| 자동화·fixture·report 검사기 | [`python`](https://github.com/seungwoo7050/guides/tree/python) |

`database-systems`와 `distributed-services`는 특정 대상 시스템을 읽을 때 도움이 되는 인접 참고 경로이지만, 현재 카탈로그가 이 브랜치에 직접 권장한 기반은 아닙니다. 데이터·분산 상태 자체의 정본 설명은 해당 브랜치에 맡깁니다.

## 브랜치와 트랙을 구분하기

`cybersecurity` 브랜치는 하나의 `field-entry` 브랜치이고, 사이버보안 트랙은 여러 브랜치를 업무 목표에 맞게 묶은 경로입니다. 둘의 완료와 실제 프로젝트 경험은 서로 대신하지 않습니다.

| 구분 | 카탈로그 계약 | 완료의 의미 |
|---|---|---|
| 이 브랜치 | 필수 기반은 `unix-systems`, `computer-networks`; `web-app`, `operating-systems`, `web-infra`, `python`, `c`, `computer-architecture`는 문제별 권장 | 이 브랜치의 네 소유 범위와 세 종료 능력을 한 합성 시스템에서 연결함 |
| 사이버보안 트랙 | 공통 `git`; 필수 `unix-systems`, `computer-networks`, `web-app`, `cybersecurity`; 권장 `operating-systems`, `web-infra`, `python`, `c`, `computer-architecture` | 공격·수정·탐지·복구 업무에 들어가기 위한 여러 기반을 함께 갖춤 |
| 실제 프로젝트 | 조직의 저장소·권한·리뷰·사용자·운영 제약 아래 변경을 완료함 | 문서나 자동 검사만으로 대체할 수 없는 반복 기여와 운영 경험을 쌓음 |

브랜치 카탈로그의 상태 값과 이 저장소의 자동 검사 통과는 현재 내용의 교육적 완성을 자동 승인하지 않습니다. 아래 추적 근거와 알려진 한계를 저자 외 사람이 검토한 뒤에만 `stable`을 판단합니다. 이 작업의 목표 상태는 **사람의 stable 검토 준비 완료**입니다.

### 이 가이드가 반복하지 않는 것

- TCP와 TLS가 동작하는 원리
- Unix permission과 process 관찰 명령 전체
- HTML·HTTP·session·CSRF의 웹 입문
- Docker·DNS·CI/CD·backup의 운영 구축 절차
- C pointer·memory allocation·thread의 언어 기초

현재 장에서 필요한 최소 상태만 요약하고 원래 브랜치로 연결합니다.

## 필수 학습 지도

### Part I. 보안 판단의 기반

1. [보안 상태와 증거](01-security-state-and-evidence.md)
2. [자산, 신뢰 경계와 위협 모델](02-assets-trust-boundaries-and-threat-models.md)
3. [평가 범위, 허가와 Rules of Engagement](03-scope-authorization-and-rules-of-engagement.md)
4. [약점, 취약점, 위험과 우선순위](04-risk-vulnerability-and-prioritization.md)

Part I이 끝나면 “위험해 보인다”는 표현을 다음 구조로 바꿀 수 있어야 합니다.

```text
보호할 상태
+ 공격자 능력
+ 필요한 전제
+ 경계를 넘는 사건
+ 관찰 가능한 영향
+ 현재 통제와 남은 위험
```

### Part II. 공격 경로와 취약점 분석

5. [공격 표면과 공격 경로](05-attack-surface-and-paths.md)
6. [애플리케이션 경계 실패](06-application-boundary-failures.md)
7. [시스템, identity와 secret 경계 실패](07-system-identity-and-secret-boundaries.md)
8. [소프트웨어 공급망과 빌드 신뢰](08-supply-chain-and-build-trust.md)
9. [취약점 검증과 보고](09-vulnerability-validation-and-reporting.md)

Part II가 끝나면 개별 finding을 나열하는 대신 다음을 설명할 수 있어야 합니다.

```text
어떤 초기 권한에서 시작했는가
→ 어떤 약점으로 새 capability를 얻었는가
→ 어떤 identity와 trust가 재사용됐는가
→ 어떤 자산에 어떤 영향이 생겼는가
→ 어디를 차단하면 경로 전체가 끊기는가
```

### Part III. 보안 엔지니어링과 대응

10. [보안 요구사항과 설계 불변식](10-security-requirements-and-design-invariants.md)
11. [보안 테스트와 assurance](11-security-testing-and-assurance.md)
12. [수정, hardening과 회귀](12-remediation-hardening-and-regression.md)
13. [보안 telemetry, 탐지와 조사](13-telemetry-detection-and-investigation.md)
14. [사고 대응과 복구](14-incident-response-and-recovery.md)
15. [보안 검토와 release 결정](15-security-review-and-release-decision.md)
16. [공격·수정·탐지 Capstone](16-capstone.md)

Part III가 끝나면 보안 변경을 “취약점 패치 완료”로 끝내지 않고 다음 수명 주기로 관리할 수 있어야 합니다.

```text
requirement
→ implementation
→ prevention test
→ detection evidence
→ incident action
→ recovery evidence
→ re-review trigger
```

## 소유 범위와 종료 근거 추적

다음 표의 첫 열은 `main` 카탈로그의 `owns`를 그대로 사용합니다. 한 문서나 검사 하나가 소유 범위 전체를 증명한다는 뜻이 아니라, 사람이 학습 결과에서 누적 근거까지 따라갈 수 있는 최소 경로입니다.

| 소유 범위 | 학습 결과와 개념 | 단계 실습·대표 실패 | Capstone 근거 |
|---|---|---|---|
| 위협 모델과 공격 표면 | 보호 상태·owner·경계·capability를 연결하고, [02장](02-assets-trust-boundaries-and-threat-models.md)과 [05장](05-attack-surface-and-paths.md)에서 edge별 전제·사건·증거를 작성함 | [01 범위와 증거](../exercises/01-scope-and-evidence/README.md), [02 위협 모델](../exercises/02-threat-model/README.md); 범위 밖 호출, network boundary를 trust boundary로 오인, 미검증 edge를 confirmed path로 표현하는 실패 | versioned scope, threat ID, attack-path edge와 검증 상태를 하나의 trace로 제출 |
| 애플리케이션·시스템 취약점 조사 | [06장](06-application-boundary-failures.md)의 애플리케이션, [07장](07-system-identity-and-secret-boundaries.md)의 system·identity, [08장](08-supply-chain-and-build-trust.md)의 artifact 경계 실패를 조사하고 [09장](09-vulnerability-validation-and-reporting.md)의 독립 근거로 후보 상태를 판정함 | [03 취약점 검증](../exercises/03-vulnerability-validation/README.md); scanner 후보를 즉시 confirmed로 선언하거나 version·configuration 불일치를 무시하는 실패 | candidate별 validation 상태, evidence, unknown, 영향과 canonical finding 관계를 제출 |
| 권한 상승·자격 증명·내부 이동의 격리 실습 | [07장](07-system-identity-and-secret-boundaries.md)의 principal·delegation·credential scope를 합성 LedgerLab 행동으로 관찰함 | [격리 attack-path 실습](../exercises/07-isolated-attack-path/README.md); cross-owner report 허용, cross-job·expired·revoked credential 허용, prefix 경계 우회 | 취약 상태, 정상 접근, 동일 공격의 거절, 상태 불변성과 audit event를 같은 실행 근거로 제출 |
| 패치·회귀 테스트·탐지·사고 복원 | [10장](10-security-requirements-and-design-invariants.md)의 requirement, [11장](11-security-testing-and-assurance.md)의 test·oracle, [12장](12-remediation-hardening-and-regression.md)의 patch·회귀, [13장](13-telemetry-detection-and-investigation.md)의 event·탐지와 [14장](14-incident-response-and-recovery.md)의 recovery를 release 검토에 연결함 | [04 요구사항](../exercises/04-security-requirements/README.md), [05 탐지](../exercises/05-detection-engineering/README.md), [06 사고 timeline](../exercises/06-incident-timeline/README.md), 격리 실습; `deny-all`, 정상 기능 회귀, 우회 경로, 탐지 누락과 신뢰하지 못한 복구 원본 | 최소 change set, 정상·경계·known-bad 회귀, deny event·alert, incident/recovery와 release decision을 연결 |

카탈로그의 세 `exit_capabilities`도 문구를 바꾸지 않고 다음 근거로 판정합니다.

| 종료 능력 | 판단할 결과 | 자동 근거와 사람 검토 |
|---|---|---|
| 허가된 환경에서 공격 경로를 증명한다 | active authorization version 안에서 edge별 precondition·action·postcondition과 합성 영향을 재현하고, 실행하지 않은 edge와 종단 간 한계를 표시함 | fixture·행동 검사는 scope ID, 허용·거절과 상태 불변성을 확인하고, 사람은 허가 적합성·인과 관계·경로 연결의 타당성을 검토 |
| root cause와 최소 패치를 만든다 | 증상이 아니라 깨진 불변식을 식별하고, 정상 기능을 보존하면서 모든 적용 경로를 복원하는 최소 change set과 회귀 근거를 제출함 | known-bad와 reference 검사는 공개 행동을 확인하고, 사람은 root cause·패치 최소성·우회 가능성을 검토 |
| 동일 공격의 차단과 탐지를 검증한다 | 같은 공격 전제와 입력을 patch 뒤 다시 실행해 거절·보호 상태 불변·audit event·detector alert를 연결함 | 자동 검사는 합성 positive·negative·duplicate·out-of-order 사례를 확인하고, 사람은 production coverage·오탐·미탐·복구 신뢰와 잔여 위험을 검토 |

## 실습 지도

01~06은 문서와 구조화 데이터 중심이고, 07은 같은 계약을 합성 행동으로 실행합니다.

| 순서 | 실습 | 핵심 결과 |
|---:|---|---|
| 1 | [범위와 증거](../exercises/01-scope-and-evidence/README.md) | 주장·근거·가설·금지 행동 구분 |
| 2 | [위협 모델](../exercises/02-threat-model/README.md) | 자산·흐름·경계·오용 사례 |
| 3 | [취약점 검증](../exercises/03-vulnerability-validation/README.md) | false positive 제거와 최소 재현 |
| 4 | [보안 요구사항](../exercises/04-security-requirements/README.md) | 위협을 testable requirement로 변환 |
| 5 | [탐지 설계](../exercises/05-detection-engineering/README.md) | event schema·analytic·triage |
| 6 | [사고 timeline](../exercises/06-incident-timeline/README.md) | 사실·가설·결정·복구 근거 |
| 7 | [격리 attack path](../exercises/07-isolated-attack-path/README.md) | 취약 상태·최소 patch·동일 공격 차단과 탐지 |

권장 반복은 다음과 같습니다.

```text
초기 자료 읽기
→ 확인된 사실과 미확인 가설 분리
→ 보호할 상태와 실패 조건 작성
→ 필요한 최소 추가 증거 결정
→ 산출물 작성
→ 반례와 잔여 위험 검토
→ rubric으로 자기 검증
```

## Capstone

[합성 서비스 보안 검토](../projects/synthetic-service-security-review/README.md)는 `LedgerLab`이라는 가상 시스템을 사용합니다.

- 공개 gateway
- account API
- report worker
- 내부 package proxy
- object storage
- audit sink
- CI와 release manifest

제공되는 것은 완성 공격 코드가 아니라 system context, asset register, manifest, 후보 finding과 event fixture입니다. 학습자는 범위·위협·finding·requirement·test·detection·incident·release decision을 직접 작성합니다.

### 필수 행동 profile과 선택 구현 profile

기본 완료 경로는 문서 분석과 Python 표준 라이브러리만 사용하는 작은 격리 행동 profile을 함께 수행합니다. 전체 서비스를 구현하는 과제가 아니라, 합성 report와 job-scoped credential에서 취약 상태, 최소 patch, 정상 기능 보존, 동일 공격의 차단·audit·탐지를 같은 공개 계약으로 다시 실행하는 과제입니다.

문서와 필수 행동 profile을 완료한 뒤에는 선택 확장으로 로컬 컨테이너에 같은 상태를 구현할 수 있습니다.

- 모든 계정과 데이터는 합성값을 사용합니다.
- network egress는 기본 거부합니다.
- host mount, privileged container와 실제 cloud credential을 사용하지 않습니다.
- 공격 성공은 synthetic flag 또는 verifier 상태로만 판정합니다.
- 각 실행 뒤 environment와 credential을 폐기합니다.

전체 로컬 service·container 구현은 필수 완료 조건이 아닙니다. 구현 전에 **어떤 상태를 만들고 어떤 실패를 검사할지**를 명확히 설계하고, 필수 행동 profile의 제한된 근거를 production 검증으로 과장하지 않는 것이 중요합니다.

## 지원 환경

- Python 3.10 이상
- POSIX 호환 셸
- GNU Make 또는 호환 `make`
- 외부 Python package 불필요
- 외부 network 불필요
- 관리자 권한 불필요

문서의 외부 표준 링크는 최신 판본을 확인하기 위한 참조입니다. 루트 자동 검증은 외부 사이트에 접속하지 않습니다.

## 준비와 검증

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 다음을 수행합니다.

- Python version 확인
- 필수 파일 존재 확인
- source fingerprint 기록
- tracked source와 분리된 ignored `.guide/` 준비 marker 생성

`verify.sh`는 다음을 수행합니다.

- Markdown 내부 링크 검사
- 필수 chapter·exercise·reference 확인
- JSON·JSONL fixture parse
- scenario ID·참조·timestamp·중복 delivery와 manifest·deploy·rollback 연결 검사
- 기준 행동 통과와 취약 skeleton·known-bad mutant 거부
- Capstone verifier의 valid fixture와 원인 코드별 invalid fixture 검사
- 기본 learner work `[SKIP]`, `CYBERSECURITY_VERIFY_WORK=1`에서만 01~07·Capstone 제출물 검사

자동 검사는 실제 취약점, 실제 권한 경계, 배포 환경과 사람의 판단을 대신하지 않습니다.

특히 자동 검사는 문서와 ID의 기계적 연결, 합성 입력에서의 공개 행동과 기준 결과를 확인합니다. threat model의 충분성, root cause의 인과성, 최소 patch의 범위, detector의 현실적 오탐·미탐, recovery trust anchor와 release authority는 사람이 제출 증거를 보고 검토합니다. 따라서 모든 검사가 통과해도 `stable`을 자동 선언하지 않습니다.

## 완료 기준

다음 산출물을 한 시스템에 대해 작성할 수 있으면 기본 과정을 완료한 것입니다.

1. scope와 Rules of Engagement
2. system context와 asset register
3. threat model과 attack-path graph
4. 검증된 finding 보고서
5. security requirement와 test plan
6. remediation·hardening·regression 계획
7. telemetry와 detection plan
8. incident timeline과 recovery evidence
9. residual risk와 release decision
10. 취약 상태의 합성 attack proof와 실행 전후 state hash
11. 구현 fingerprint, canonical skeleton 대비 patch diff와 최소성 근거
12. 정상·경계·known-bad 회귀, corrected deny event와 detector positive·negative evidence
13. cleanup 결과와 합성 profile이 보장하지 않는 범위

그리고 다음 행동이 가능해야 합니다.

- 기존 보안 issue의 재현 조건을 검토합니다.
- 보안 테스트나 regression fixture를 추가합니다.
- 작은 취약점의 root cause를 수정합니다.
- 같은 actor·resource·action을 재실행해 수정 뒤 차단과 탐지를 확인합니다.
- 로그·탐지·runbook의 누락을 보완합니다.
- 자신이 확인하지 못한 범위와 추가 검토가 필요한 전문가 영역을 명시합니다.

## 이후 확장

이 가이드는 공통 진입점입니다. 다음 영역은 실제 프로젝트와 별도 전문 과정에서 확장합니다.

- Offensive Security와 고급 penetration testing
- exploit development와 vulnerability research
- Security Engineering과 product-wide secure architecture
- Detection Engineering, threat hunting과 DFIR
- Cloud·Kubernetes·identity 전문 보안
- Mobile·embedded·OT 보안
- AI model·agent 보안
- Governance, Risk and Compliance

[프로젝트 진입 지도](../reference/project-entry-map.md)는 가이드 이후의 기여 형태를 정리합니다.
