# 표준과 외부 자료 지도

이 문서는 본문이 사용하는 외부 표준의 역할을 구분합니다. checklist를 모두 적용하는 것이 목표가 아니라, 현재 문제에 필요한 판본과 항목을 선택하고 자신의 requirement·test·evidence에 연결합니다.

## 1. 위험 관리와 운영 수명 주기

### NIST Cybersecurity Framework 2.0

- URL: <https://www.nist.gov/cyberframework>
- 역할: Govern, Identify, Protect, Detect, Respond, Recover의 상위 outcome 지도
- 사용 위치: threat model, review packet, incident·recovery coverage 확인
- 한계: 구체적인 구현과 test method를 직접 규정하지 않음

### NIST SP 800-61 Rev. 3

- URL: <https://csrc.nist.gov/pubs/sp/800/61/r3/final>
- 역할: CSF 2.0에 통합된 incident response 권고
- 사용 위치: 준비, detection·response·recovery, post-incident improvement

## 2. 보안 평가

### NIST SP 800-115

- URL: <https://csrc.nist.gov/pubs/sp/800/115/final>
- 역할: 기술 보안 test와 assessment의 계획·수행·분석·완화 개요
- 주의: 2008년 문서이므로 현대 cloud·container·supply-chain 세부는 다른 최신 자료로 보완

### OWASP Web Security Testing Guide

- URL: <https://owasp.org/www-project-web-security-testing-guide/>
- stable: 4.2
- latest development: 5.0 개발 중
- 역할: web application·service test scenario 설계
- 사용 방법: 문서에 versioned scenario ID를 기록하고 현재 scope에 맞게 선택

## 3. 애플리케이션 보안 requirement

### OWASP Application Security Verification Standard 5.0.0

- URL: <https://owasp.org/www-project-application-security-verification-standard/>
- 역할: web application의 testable technical security requirement
- 사용 방법: `v5.0.0-<requirement>` 형식으로 version을 포함해 trace
- 한계: threat model·business context·runtime evidence를 대신하지 않음

### OWASP Cheat Sheet Series

- URL: <https://cheatsheetseries.owasp.org/>
- 역할: 특정 control 구현의 실무 참고
- 사용 방법: 원래 framework·language 문서와 함께 검증

## 4. 약점과 공격 행동 vocabulary

### CWE 4.20

- URL: <https://cwe.mitre.org/data/index.html>
- 판본: 4.20 (2026-04-30 공개)
- 역할: software·hardware weakness와 root cause mapping
- 사용 위치: finding 분류, similar-path search, recurrence prevention
- 주의: CWE ID 자체가 severity나 exploitability를 의미하지 않음

### CAPEC 3.9

- URL: <https://capec.mitre.org/data/downloads>
- 판본: 3.9
- 역할: attack pattern vocabulary
- 사용 위치: threat brainstorming과 abuse case

### MITRE ATT&CK 19.2

- URL: <https://attack.mitre.org/resources/versions/>
- 이 브랜치의 mapping 기준: 19.2 (2026-08-09 공식 live version history 확인)
- 역할: 실제 관찰 기반 adversary tactics·techniques와 Detection Strategies·Analytics·Data Components vocabulary
- 사용 위치: attack-path context, detection coverage, simulation
- 한계: system-specific threat model이나 보안 control checklist가 아니며, object별 version·revocation·deprecation이 바뀔 수 있음
- 사용 방법: technique ID만 복사하지 않고 mapping에 사용한 catalog version과 object version 또는 version permalink를 기록

## 5. 취약점 severity

### FIRST CVSS 4.0

- URL: <https://www.first.org/cvss/v4.0/>
- 역할: vulnerability의 Base·Threat·Environmental 특성 구조화
- 사용 위치: finding severity 근거
- 주의: Attack Complexity와 Attack Requirements를 구분하고, Vulnerable System·Subsequent System impact를 각각 기록
- 한계: Supplemental metrics는 문맥을 전달하지만 CVSS-BTE 점수를 바꾸지 않으며, 조직 priority와 risk acceptance를 score 하나로 대체하지 않음

## 6. secure development와 공급망

### NIST SP 800-218 SSDF 1.1

- URL: <https://csrc.nist.gov/pubs/sp/800/218/final>
- 역할: secure development practice를 SDLC에 통합하는 공통 framework
- 판본 메모: 1.1은 Final

### NIST SP 800-218 Rev. 1 SSDF 1.2

- URL: <https://csrc.nist.gov/pubs/sp/800/218/r1/ipd>
- 판본 메모: 2025-12-17 Initial Public Draft이며 1.1 Final을 자동 대체하지 않음
- 사용 방법: 1.2의 추가·변경 practice를 사용하면 draft임을 표시하고 1.1 mapping과 구분

### SLSA 1.2

- URL: <https://slsa.dev/spec/v1.2/>
- 상태: Approved
- 역할: source·build supply-chain threat, provenance와 verification
- 사용 위치: source-to-artifact trust graph와 release evidence
- 한계: level·attestation은 명시한 source·build property의 근거이며 artifact의 무취약성이나 production 허용을 보장하지 않음

### OpenSSF Scorecard

- URL: <https://scorecard.dev/>
- 분류와 확인 기준: versioned 표준이 아니라 도구이며, 이 문서의 확인 시점 release는 5.5.0
- 역할: open-source project의 자동화 가능한 supply-chain practice 신호
- 주의: score는 project security 전체와 특정 release 안전을 보장하지 않음

### CISA Secure by Design

- URL: <https://www.cisa.gov/securebydesign>
- 분류와 확인 기준: versioned 표준이 아니라 living initiative이며, 2023-10 refined joint guide를 기준으로 확인
- 역할: 제조자가 안전한 기본값과 vulnerability class 제거 책임을 제품 설계에 포함하는 원칙

## 7. vulnerability disclosure

### NIST SP 800-216 — Recommendations for Federal Vulnerability Disclosure Guidelines

- URL: <https://csrc.nist.gov/pubs/sp/800/216/final>
- 역할: 미국 연방 통제 아래 software·hardware·digital service를 위한 vulnerability disclosure framework 수립 권고
- 한계: 모든 조직에 적용되는 보편적 법률 자문, safe harbor 문구 또는 관할별 공개 절차를 대신하지 않음

### SECURITY.md

- URL: <https://docs.github.com/en/code-security/getting-started/adding-a-security-policy-to-your-repository>
- 역할: repository별 private reporting channel과 지원 version 확인

## 8. 사용 규칙

1. 문서에 표준 이름과 version을 기록합니다.
2. requirement ID를 인용하면 판본을 함께 적습니다.
3. 표준이 해결하는 문제와 해결하지 않는 문제를 구분합니다.
4. 자신의 system context와 threat에 맞지 않는 항목을 기계적으로 적용하지 않습니다.
5. 표준 update 뒤 기존 mapping이 여전히 유효한지 검토합니다.
6. 본문과 표준이 다르면 현재 공식 판본을 확인하고 issue 또는 변경으로 남깁니다.
7. CWE·CAPEC·ATT&CK 같은 living catalog는 학습 시작과 review 시점에 version history를 다시 확인하고, mapping 결과에는 실제 사용한 snapshot을 고정합니다.
8. 표준, guide, living catalog와 도구를 같은 갱신 계약으로 취급하지 않습니다. 표준·guide는 판본과 status, catalog는 snapshot, 도구는 실행 version을 기록합니다.

최종 확인 기준일: **2026-08-09**.
