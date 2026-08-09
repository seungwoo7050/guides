# 사이버보안 분석·검증·대응 가이드

사이버보안을 별도의 “방어 이론”과 “해킹 도구 사용법”으로 나누지 않고, 하나의 시스템을 다음 순서로 다루는 가이드입니다.

```text
보호할 상태와 신뢰 경계를 정의합니다.
→ 공격자가 악용할 수 있는 전제와 경로를 찾습니다.
→ 허가된 격리 환경에서 최소한의 증거로 검증합니다.
→ 원인을 수정하고 회귀 검사를 추가합니다.
→ 탐지·대응·복구까지 같은 계약으로 연결합니다.
```

이 브랜치의 목적은 보안 전문가를 한 번에 완성하는 것이 아닙니다. 개발자가 애플리케이션 보안, 제품 보안, 보안 자동화, 취약점 분석, 탐지·대응 프로젝트에 합류할 때 필요한 공통 언어와 작업 순서를 제공합니다.

처음에는 [`docs/00-roadmap.md`](docs/00-roadmap.md)를 읽으세요. 선행 가이드와의 경계, 필수 문서 순서, 문서 중심 실습, Capstone과 완료 기준을 한곳에서 확인할 수 있습니다.

## 시작하기 전에

이 브랜치는 웹·백엔드·시스템·인프라의 기본 구현 경험이 있고, 이미 존재하는 시스템의 보안 주장을 **허가된 범위에서 증거로 검토하고 수정하는 법**을 배우려는 독자를 위한 분야 진입 과정입니다. 프로그래밍과 운영의 첫 입문 과정은 아닙니다.

- 필수 기반: `unix-systems`의 파일·권한·process·socket 관찰 능력, `computer-networks`의 DNS·IP·transport·TLS·HTTP 계층 구분 능력
- 작업 기반: Git으로 변경을 비교하고, 셸 명령을 실행하며, Markdown·JSON을 읽고 수정하는 능력
- 문제별 보완: 웹 경계는 `web-app`, process·memory 경계는 `operating-systems`, 공개 운영 경계는 `web-infra`를 먼저 확인합니다.

`cybersecurity` **브랜치 완료**는 아래 소유 범위와 종료 능력을 한 합성 시스템에서 연결했다는 뜻입니다. `main`의 **사이버보안 트랙 완료**는 `git`, `unix-systems`, `computer-networks`, `web-app`을 포함한 더 넓은 준비 상태이며, 실제 프로젝트 경험을 대신하지 않습니다. 정확한 차이와 권장 순서는 [roadmap의 브랜치와 트랙 구분](docs/00-roadmap.md#브랜치와-트랙을-구분하기)에서 확인합니다.

## 과정이 만드는 능력

과정을 마치면 다음 작업을 수행할 수 있어야 합니다.

- 보안 목표를 제품 기능이 아니라 보호할 자산·상태·불변식으로 작성합니다.
- 시스템 경계, 행위자, 신뢰 수준, 자격 증명과 데이터 흐름을 한 장의 위협 모델로 연결합니다.
- 허가 범위, 금지 행동, 중단 조건, 증거 보존과 제3자 경계를 포함한 평가 계약을 작성합니다.
- 약점, 노출, 취약점, 공격 전제, 영향과 실제 사건을 서로 다른 개념으로 구분합니다.
- 개별 취약점보다 여러 권한·설정·신뢰 문제가 이어지는 공격 경로를 분석합니다.
- 애플리케이션·시스템·identity·secret·공급망 경계의 대표 실패를 원인과 검사 관점에서 설명합니다.
- 자동 도구의 경고를 그대로 취약점으로 선언하지 않고, 최소 재현과 독립 근거로 참·거짓을 판단합니다.
- 위협을 검증 가능한 보안 요구사항과 정상·경계·실패 테스트로 바꿉니다.
- 정적 분석, 동적 분석, fuzzing, dependency·configuration 검사와 수동 평가가 보장하는 범위를 구분합니다.
- 패치, hardening, 자격 증명 회전, 데이터 정리, 회귀 검사와 재검증을 하나의 수정 계획으로 만들고, 합성 구현에서 최소 패치를 적용합니다.
- 보안 사건을 재구성할 수 있는 로그 schema와 탐지 가설을 설계합니다.
- 사고 중 사실·가설·결정을 분리하고, 증거를 보존하며, containment·eradication·recovery를 검증합니다.
- release 전에 잔여 위험과 근거의 유효 기간을 포함한 보안 검토 결정을 내립니다.

## 이 브랜치가 소유하는 범위

`main` 카탈로그가 정한 소유 범위는 다음 네 가지입니다. 이 문구를 넓히거나 줄이지 않고, 아래의 세부 학습 항목으로 풀어냅니다.

- 위협 모델과 공격 표면
- 애플리케이션·시스템 취약점 조사
- 권한 상승·자격 증명·내부 이동의 격리 실습
- 패치·회귀 테스트·탐지·사고 복원

```text
보안 상태와 증거
+ 위협 모델과 평가 범위
+ 취약점·공격 경로 분석
+ 보안 요구사항과 검증 전략
+ 수정·회귀·hardening
+ 탐지·사고 대응·복구
+ 보안 검토와 잔여 위험 결정
```

다음 기반은 기존 브랜치가 소유합니다.

| 기반 | 주 소유 브랜치 | 이 브랜치에서 사용하는 방식 |
|---|---|---|
| 파일·프로세스·권한·socket 관찰 | [`unix-systems`](https://github.com/seungwoo7050/guides/tree/unix-systems) | 공격·방어 가설의 증거를 수집합니다. |
| Ethernet·IP·TCP·DNS·TLS·방화벽 | [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) | 공격 경로와 최초 실패 계층을 구분합니다. |
| process·memory·concurrency·filesystem | [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems) | 권한·격리·메모리·race 문제의 기반으로 참조합니다. |
| HTTP·세션·권한·CSRF·CORS | [`web-app`](https://github.com/seungwoo7050/guides/tree/web-app) | 보안 속성이 깨지는 조건과 회귀 검사를 분석합니다. |
| 공개 호스트·secret·release·backup·incident | [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra) | 운영 통제가 실제 공격 경로를 어디서 차단하는지 검토합니다. |
| C 메모리와 sanitizer | [`c`](https://github.com/seungwoo7050/guides/tree/c) | 저수준 취약점 입문의 구현·검증 기반으로 사용합니다. |
| CPU·memory hierarchy·privilege 기초 | [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture) | 저수준 경계의 전제를 확인하되 architecture 자체를 다시 가르치지 않습니다. |
| 자동화·CLI·구조화 데이터 | [`python`](https://github.com/seungwoo7050/guides/tree/python) | 증거 정리와 작은 검사기를 구현하는 선택 경로로 사용합니다. |

이 브랜치는 위 내용을 다시 가르치지 않습니다. 각 기반이 **공격 전제, 보안 불변식, 증거와 수정 계약**으로 어떻게 연결되는지에 집중합니다.

## 학습 구조

### Part I. 보안 판단의 기반

1. [보안 상태와 증거](docs/01-security-state-and-evidence.md)
2. [자산, 신뢰 경계와 위협 모델](docs/02-assets-trust-boundaries-and-threat-models.md)
3. [평가 범위, 허가와 Rules of Engagement](docs/03-scope-authorization-and-rules-of-engagement.md)
4. [약점, 취약점, 위험과 우선순위](docs/04-risk-vulnerability-and-prioritization.md)

### Part II. 공격 경로와 취약점 분석

5. [공격 표면과 공격 경로](docs/05-attack-surface-and-paths.md)
6. [애플리케이션 경계 실패](docs/06-application-boundary-failures.md)
7. [시스템, identity와 secret 경계 실패](docs/07-system-identity-and-secret-boundaries.md)
8. [소프트웨어 공급망과 빌드 신뢰](docs/08-supply-chain-and-build-trust.md)
9. [취약점 검증과 보고](docs/09-vulnerability-validation-and-reporting.md)

### Part III. 보안 엔지니어링과 대응

10. [보안 요구사항과 설계 불변식](docs/10-security-requirements-and-design-invariants.md)
11. [보안 테스트와 assurance](docs/11-security-testing-and-assurance.md)
12. [수정, hardening과 회귀](docs/12-remediation-hardening-and-regression.md)
13. [보안 telemetry, 탐지와 조사](docs/13-telemetry-detection-and-investigation.md)
14. [사고 대응과 복구](docs/14-incident-response-and-recovery.md)
15. [보안 검토와 release 결정](docs/15-security-review-and-release-decision.md)
16. [공격·수정·탐지 Capstone](docs/16-capstone.md)
17. [표준과 외부 자료 지도](docs/90-standards-map.md)

## 단계 실습과 격리 행동 실습

실습은 실제 외부 시스템을 공격하지 않습니다. 01~06은 프로젝트에서 필요한 보안 산출물을 직접 작성하고, 07은 Python 표준 라이브러리와 합성 상태만으로 취약 상태·최소 패치·동일 공격 차단·탐지를 실행합니다.

| 실습 | 결과물 |
|---|---|
| [01 범위와 증거](exercises/01-scope-and-evidence/README.md) | 평가 범위, 보안 주장, 근거와 중단 조건 |
| [02 위협 모델](exercises/02-threat-model/README.md) | 자산·행위자·흐름·경계·오용 사례 |
| [03 취약점 검증](exercises/03-vulnerability-validation/README.md) | 후보 finding의 참·거짓 판정과 최소 재현 계획 |
| [04 보안 요구사항](exercises/04-security-requirements/README.md) | 위협에서 도출한 requirement와 회귀 검사 |
| [05 탐지 설계](exercises/05-detection-engineering/README.md) | event schema, detection hypothesis와 triage 절차 |
| [06 사고 timeline](exercises/06-incident-timeline/README.md) | 사실·가설·결정·복구 근거가 분리된 timeline |
| [07 격리 attack path](exercises/07-isolated-attack-path/README.md) | cross-owner·cross-job 공격 proof, 최소 patch, 회귀·audit·탐지 evidence |

문서 실습은 정답 문구를 강제하지 않고 초기 자료, 필수 산출물, 허용 범위, 대표 오답과 사람 검토 질문을 제공합니다. 07은 취약 `skeleton`과 기준 `reference`를 제공하지만 구현 모양이 아니라 허용·거부 결정, 보호 상태의 불변성, audit event와 detector alert를 검사합니다.

## Capstone

[`projects/synthetic-service-security-review`](projects/synthetic-service-security-review/README.md)는 가상의 다중 서비스 시스템을 대상으로 다음을 수행합니다.

```text
평가 계약
→ 위협 모델
→ 공격 경로
→ finding 검증
→ 보안 요구사항
→ 수정·회귀 계획
→ 탐지 규칙
→ 사고 timeline
→ release 결정
```

필수 profile은 제공된 문서·manifest·event fixture 분석과 작은 격리 행동 실습을 함께 수행합니다. 취약 상태 proof, 실제 최소 patch와 diff, 정상·경계·known-bad 회귀, 동일 공격의 거부 event와 탐지 결과를 하나의 trace에 연결합니다. 전체 로컬 service·container 구현은 선택 확장입니다. 실제 인터넷, 제3자 계정, 실제 자격 증명과 production 데이터는 사용하지 않습니다.

## 안전 범위

- 자신이 소유하거나 명시적으로 허가받은 환경만 평가합니다.
- 기본 실습은 저장소 파일, loopback, 로컬 임시 디렉터리와 합성 데이터만 사용합니다.
- 외부 주소 scan, 계정 추측, credential stuffing, phishing, persistence, 방어 회피와 데이터 반출을 실습하지 않습니다.
- 취약점 증명은 영향에 필요한 최소 범위에서 중단합니다.
- 실제 credential·비밀값·session·개인정보와 운영 로그를 저장소에 넣지 않습니다.
- 제3자 서비스가 경로에 포함되면 그 서비스는 범위 밖으로 표시하고 테스트하지 않습니다.
- 중단 조건과 복구 절차가 없는 실험은 시작하지 않습니다.

자세한 기준은 [안전한 실습 정책](reference/safe-lab-policy.md)에 있습니다.

## 준비와 검증

Python 3.10 이상과 POSIX 호환 셸만 필요합니다. 외부 package나 Docker는 루트 검증의 필수 조건이 아닙니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 source를 바꾸지 않고 문서·fixture fingerprint와 Python 환경을 기록합니다. `verify.sh`는 다음을 확인합니다.

1. 필수 문서와 실습 구조
2. 내부 Markdown 링크
3. JSON·JSONL fixture 형식
4. Capstone 산출물 검사기의 자체 테스트
5. 안전 정책과 필수 경계 문서의 존재

실제 취약점의 발견이나 특정 제품의 보안성을 자동으로 보장하지 않습니다.

검사 통과는 파일·링크·fixture와 기준 행동의 재현 근거일 뿐, 설명의 정확성이나 학습 경로의 충분성 또는 `stable`을 자동으로 증명하지 않습니다. 저자 외 사람이 문서·실습·Capstone의 정상·경계·대표 실패와 종료 근거를 검토해야 하며, 이 브랜치가 목표로 하는 상태는 **사람의 stable 검토 준비 완료**입니다.

## 종료 기준

카탈로그가 선언한 종료 능력은 다음 세 가지입니다.

1. 허가된 환경에서 공격 경로를 증명한다.
2. root cause와 최소 패치를 만든다.
3. 동일 공격의 차단과 탐지를 검증한다.

여기서 “증명”은 명시한 version·scope·초기 상태와 증거 범위에 한정됩니다. 한 edge의 재현이 전체 공격 경로의 종단 간 성공을 뜻하지 않고, 기준 구현의 통과가 production 보안을 보장하지 않습니다. [roadmap의 추적표](docs/00-roadmap.md#소유-범위와-종료-근거-추적)에서 각 능력의 개념 문서·단계 실습·대표 실패·Capstone 근거를 확인합니다.

다음 질문에 도구 이름이 아니라 **상태, 전제, 증거와 잔여 위험**으로 답할 수 있어야 합니다.

1. 무엇을 보호하며, 어떤 상태 변화가 보안 실패입니까?
2. 공격자가 경계를 넘기 위해 필요한 전제는 무엇입니까?
3. 스캐너 경고가 실제 취약점인지 어떤 최소 근거로 판정합니까?
4. 개별 약점이 어떻게 하나의 공격 경로로 이어집니까?
5. 수정이 증상만 막은 것인지 원인을 제거한 것인지 어떻게 구분합니까?
6. 같은 취약점 계열이 다시 생기지 않도록 어떤 검사와 개발 규칙을 추가합니까?
7. 공격 시도를 조사할 수 있도록 어떤 event가 남아야 합니까?
8. 사고 중 증거를 지우지 않으면서 어떤 조치를 먼저 수행합니까?
9. release를 허용할 때 어떤 잔여 위험을 누가 언제까지 수용합니까?
10. 이 가이드 이후 어떤 실제 프로젝트에서 어떤 작은 기여부터 시작합니까?

## 범위 밖

- 무단 침투, 실제 표적 공격과 공격 인프라 운영
- 고급 exploit 개발, malware 개발, evasion과 장기 persistence
- enterprise identity, Active Directory, cloud 보안 제품 전체
- 디지털 포렌식의 전문 수집·법적 절차 전체
- OT·ICS, 모바일, 임베디드와 AI 전용 보안 과정 전체
- 규제·감사·GRC 프로그램의 완전한 운영

이 영역은 공통 진입 능력을 만든 뒤 별도 전문 과정과 실제 프로젝트에서 확장합니다.

## 다음 프로젝트 경로

완료 뒤에는 [프로젝트 진입 지도](reference/project-entry-map.md)를 사용해 실제 저장소의 작은 보안 변경으로 이동합니다. 먼저 기존 security issue의 재현 조건 검토, 허가·회귀 fixture 추가, object authorization의 작은 patch, audit event·탐지 규칙 또는 incident runbook 보완처럼 검토 가능한 단위를 선택합니다. 여러 팀의 배포·정책·관측·복구 경로를 제품으로 만들려면 `platform-engineering`으로 이어가고, 고급 침투 테스트·exploit 연구·DFIR·GRC는 현재 카탈로그의 내부 후속 브랜치가 아니라 외부 전문 과정과 조직의 승인 절차에서 확장합니다.
