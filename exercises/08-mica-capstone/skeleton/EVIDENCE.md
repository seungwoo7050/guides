# Mica capstone completion evidence

이 문서는 실행 로그를 붙이는 장소이자 사람 검토 판정표입니다. 공개 runner의 성공만으로 완료를 표시하지 않습니다. 각 항목은 `충족`, `보완 필요`, `허용된 변형` 중 하나로 판정하고 근거 파일·명령·revision을 연결합니다. 미해결 `보완 필요`가 하나라도 있으면 capstone은 완료되지 않았습니다.

## 환경과 revision

- 구현 revision:
- 운영체제/architecture:
- Python/compiler/LLVM 및 dependency version:
- target triple/data layout(해당 시):

## Core conformance

- 실행 명령:
- `lex`·`parse` token/AST golden 결과:
- `check` symbol/type/flow 결과:
- tree-walk `run` 정상·runtime 실패 결과:
- 학습자가 추가한 정상 fixture 3개 이상:
- 학습자가 추가한 phase별 실패 fixture 5개 이상:
- 판정:

## 필수 IR·CFG·data-flow·pass 증거

- typed AST→normalized IR lowering dump:
- malformed CFG를 실행 전에 거부한 verifier 결과:
- loop가 있는 CFG의 fixed-point trace:
- pass 전/후 IR, `changed`, invalidated analysis와 verifier 재실행:
- 정상 return/stdout 및 runtime diagnostic differential:
- trap/effect를 지우는 known-bad pass 거부 결과:
- 판정:

## 선택 실행 경로

- 선택: bytecode VM / LLVM·다른 backend
- valid compile·artifact·disassembly:
- interpreter와 stdout·return·diagnostic differential:
- invalid bytecode/IR 또는 unsupported feature 거부:
- 자원·권한·cleanup·복구 기록:
- 판정:

## 선택 tooling 경로

- 선택: formatter+linter / LSP subset
- formatter exact output·comment·idempotence·parse/check round-trip:
- lint code·정렬·false positive/negative·unsafe fix:
- 또는 LSP Unicode position·document version·stale result·protocol channel:
- 판정:

## Known-bad와 검증기 한계

- known-bad 변경과 기대 실패:
- 실제 거부 명령/결과:
- 자동 검사가 보장하는 공개 행동:
- parser 종료성·type soundness·optimizer 의미 보존 등 보장하지 않는 것:
- 판정:

## 사람 검토

| 종료 능력 | 필요한 설명과 증거 | 판정 | 검토자/날짜 |
|---|---|---|---|
| 작은 언어의 frontend를 만듭니다 | recovery 진행, token/source slice, normalized AST와 diagnostic |  |  |
| 정적 타입과 실행 모델을 구현합니다 | SymbolId/type/flow 범위, runtime 상태·budget·실패 |  |  |
| 분석·진단·변환 도구를 확장합니다 | IR/pass 의미 보존과 선택 tooling의 한계 |  |  |

## Cleanup과 복구

- workspace 백업 위치:
- 생성 artifact와 제거 명령:
- 중단/손상 뒤 새 workspace 또는 복구 절차:
- host가 아닌 container/VM이 필요한 실행:
