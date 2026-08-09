# 표준과 참고 자료

검토일: 2026-08-10

이 문서는 에이전트 runtime을 설계할 때 확인할 공식 문서와 1차 자료의 시작점입니다. 코딩 에이전트가 이 가이드의 주 구현 프로필이지만 model·RAG·tool·durable state·policy·evaluation 원칙은 특정 작업 도메인이나 제품 UI에 종속시키지 않습니다. 실제 구현 시 사용하는 version과 revision을 고정하고 최신 security note를 다시 확인합니다.

## 실제 코딩 에이전트의 기능 경계

### OpenAI Codex

- [Introducing Codex](https://openai.com/index/introducing-codex/): 격리 환경에서 저장소를 읽고 수정하며 test·lint·type checker를 반복 실행하고 terminal log와 test 결과를 검토 근거로 제공하는 software-engineering agent의 공개 설명
- [Codex is now generally available](https://openai.com/index/codex-now-generally-available/): CLI·cloud·SDK와 조직 운영 방향
- [openai/codex](https://github.com/openai/codex): terminal coding agent의 공식 오픈소스 저장소
- [Codex documentation](https://developers.openai.com/codex/): configuration, sandbox, approval와 사용 경계

### Anthropic Claude Code

- [Claude Code overview](https://docs.anthropic.com/en/docs/claude-code/overview): terminal 기반 agentic coding tool의 공식 개요
- [CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage): interactive·print mode, session resume, turn limit와 output mode
- [Security](https://docs.anthropic.com/en/docs/claude-code/security): permission 기반 실행, file write와 command 승인, prompt injection과 격리 권고
- [Identity and access management](https://docs.anthropic.com/en/docs/claude-code/iam): tool permission, allow·deny와 permission mode
- [Memory](https://docs.anthropic.com/en/docs/claude-code/memory): project·user instruction과 directory scope의 실제 사례
- [Claude Code SDK](https://docs.anthropic.com/en/docs/claude-code/sdk): structured event, session, allowed tool과 programmatic control 사례

제품 문서는 “무엇이 가능한가”와 실제 UX 사례를 이해하는 데 사용합니다. 이 가이드의 tool, permission, checkpoint와 verifier contract는 제품별 옵션과 독립적으로 설계합니다.

## 코딩 과제 평가

- [SWE-bench repository](https://github.com/SWE-bench/SWE-bench): 실제 GitHub issue와 repository patch를 containerized test harness로 평가하는 benchmark와 공식 실행기
- [SWE-bench evaluation guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md): patch 적용, Docker environment와 test 기반 판정 절차
- [SWE-agent repository](https://github.com/SWE-agent/SWE-agent): repository issue 해결 agent와 agent-computer interface 연구 구현
- [HAL harness](https://github.com/princeton-pli/hal-harness): 여러 agent benchmark를 재현 가능한 공통 harness로 실행하는 연구 구현

공개 benchmark는 contamination, task selection과 evaluator error의 한계가 있습니다. 제품 release gate에는 자체 private fixture와 security regression을 함께 사용합니다.

## Tool protocol과 상호 운용성

- [Model Context Protocol specification](https://modelcontextprotocol.io/specification/latest): tool·resource·prompt 연결 protocol
- [MCP security best practices](https://modelcontextprotocol.io/specification/latest/basic/security_best_practices): authorization, consent, credential와 network 경계
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12): model action과 tool input/output의 구조 검증

MCP를 사용해도 tool server trust, path·command policy, sandbox, approval, effect ledger와 verifier는 별도로 필요합니다.

## 모델 API, RAG와 provenance

- [HTTP Semantics, RFC 9110](https://www.rfc-editor.org/rfc/rfc9110): provider-compatible adapter의 request·response·status·retry 경계를 해석하는 1차 표준
- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401): retrieval과 generation을 결합한 RAG 원 논문의 출발점
- [W3C PROV Overview](https://www.w3.org/TR/prov-overview/): source·entity·activity·agent provenance를 표현하는 표준 지도
- [NIST SP 800-162, Guide to Attribute Based Access Control](https://doi.org/10.6028/NIST.SP.800-162): principal·resource·environment attribute로 retrieval·tool 권한을 판정하는 기반

RAG reference는 retrieval 뒤 민감한 결과를 display에서 가리는 방식이 아니라 **authorization-before-retrieval**을 사용합니다. 허가된 결과도 origin·scope·revision·digest를 context와 citation에 보존하고, stale·conflicting source와 no-evidence를 서로 다른 상태로 남깁니다. 이 가이드의 로컬 repository 검색은 RAG의 구체 적용이며 일반 vector database나 embedding 모델 전체를 다시 가르치지 않습니다.

## AI와 agent 보안

- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework): AI 위험의 govern·map·measure·manage 구조
- [NIST AI Agent Standards Initiative](https://www.nist.gov/artificial-intelligence/ai-agent-standards-initiative): agent 상호 운용성과 안전을 위한 표준화 프로그램
- [NIST AI Agent Identity and Authorization Concept Paper](https://csrc.nist.gov/pubs/other/2026/02/05/accelerating-the-adoption-of-software-and-ai-agent/ipd): agent identity, authorization와 delegation 문제
- [OWASP Agentic AI Threats and Mitigations](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/): tool misuse, authority, memory와 목표 관련 위협
- [OWASP Securing Agentic Applications Guide](https://genai.owasp.org/resource/securing-agentic-applications-guide-1-0/): agentic application의 설계·방어 출발점

## 관측성

- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/): trace·metric·log의 공통 의미
- [OpenTelemetry Generative AI conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/): model·agent·tool operation을 표현하는 experimental convention

experimental schema는 그대로 영구 저장 형식으로 고정하지 않고 내부 versioned event에 mapping합니다.

## 운영체제·Git 1차 자료

- [Git documentation](https://git-scm.com/docs): worktree, diff, index, reset·restore·revert와 plumbing command
- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html): Python 구현 프로필의 process 생성·stream·timeout 경계
- [POSIX.1 process and file interfaces](https://pubs.opengroup.org/onlinepubs/9799919799/): process, signal, file descriptor와 path 동작의 표준 출발점

## 사용 원칙

- 제품 feature를 보편적인 architecture requirement와 구분합니다.
- mutable `latest` 문서만 기록하지 않고 구현 manifest에 실제 version과 revision을 고정합니다.
- benchmark 점수를 실제 사용자 생산성이나 안전성 전체로 해석하지 않습니다.
- protocol·framework가 해결하지 않는 permission, sandbox, effect와 verifier 경계를 직접 문서화합니다.
- 필수 model adapter 검증은 scripted scenario와 loopback provider fixture로 offline 재현하고, 실제 API key·public network·유료 call을 요구하지 않습니다.
- live provider smoke를 실행하지 않았으면 명시적으로 미실행으로 남기며, loopback 통과를 provider 품질이나 production availability의 증거로 과장하지 않습니다.
- retrieval source의 license·권한·version과 citation digest를 evaluation artifact에 기록합니다.
- 외부 오픈소스에 기여할 때 해당 repository의 현재 architecture와 contribution policy를 다시 조사합니다.
