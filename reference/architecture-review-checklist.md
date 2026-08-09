# Architecture review checklist

## 목표와 범위

- [ ] 결과물이 일반 AI 앱이 아니라 coding-agent runtime임을 설명합니다.
- [ ] local interactive, headless, cloud 등 지원 profile을 구분합니다.
- [ ] remote push·deploy·multi-agent 같은 비범위를 명시합니다.

## 구성요소

- [ ] model adapter와 runtime이 분리돼 있습니다.
- [ ] repository explorer와 context manager가 분리돼 있습니다.
- [ ] tool gateway, policy, sandbox와 verifier가 분리돼 있습니다.
- [ ] transcript와 durable event log가 분리돼 있습니다.

## 저장소와 Git

- [ ] HEAD·index·working tree·initial dirty state를 snapshot합니다.
- [ ] agent change와 사용자 change를 구분합니다.
- [ ] stale file digest와 workspace divergence를 탐지합니다.
- [ ] rollback이 사용자 기존 작업을 지우지 않습니다.

## Tool과 process

- [ ] 자유 shell 문자열이 기본 tool이 아닙니다.
- [ ] path canonicalization과 symlink를 처리합니다.
- [ ] multi-file patch에 precondition과 receipt가 있습니다.
- [ ] command에 argv·cwd·env·timeout·output·process tree가 있습니다.
- [ ] cancel 뒤 child process와 resource를 확인합니다.

## Coding loop

- [ ] task acceptance와 non-goal이 있습니다.
- [ ] 사실과 가설을 구분합니다.
- [ ] edit-test-repair iteration이 기록됩니다.
- [ ] failure category가 다음 행동을 제한합니다.
- [ ] 반복 정지와 사용자 질문 조건이 있습니다.

## 안전

- [ ] repository content를 untrusted data로 처리합니다.
- [ ] permission이 prompt 밖에서 강제됩니다.
- [ ] network·secret·dependency 경계를 분리합니다.
- [ ] verifier와 hidden test가 agent에서 분리됩니다.
- [ ] kill·revoke·quarantine과 사고 증거가 있습니다.

## 평가

- [ ] known-good와 known-bad patch로 verifier를 검사합니다.
- [ ] behavior, regression, policy와 evaluation error를 분리합니다.
- [ ] final diff와 마지막 test revision이 같습니다.
- [ ] model·runtime·tool·policy·environment identity를 기록합니다.
