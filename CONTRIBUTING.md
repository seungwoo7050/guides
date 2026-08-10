# 기여 안내

문서, 상태 모델과 검증은 같은 계약을 가리켜야 합니다. 특정 보드에서 한 번 동작했다는 사실을 전체 MCU·RTOS의 보장으로 확대하지 않습니다.

## 문서를 고칠 때

- 자연스러운 한국어 경어체를 사용합니다.
- register, ISR, DMA, deadline 같은 원어가 검색과 명세 확인에 필요하면 첫 등장에 함께 적습니다.
- `c`, `computer-architecture`, `operating-systems`가 이미 소유하는 원리는 짧게 연결하고 반복하지 않습니다.
- hardware 보장, RTOS API 보장, application 정책과 관찰 결과를 구분합니다.
- register bit, interrupt number, flash address와 timing 수치는 사용하는 SoC·board·문서 판본을 함께 적습니다.
- 한 vendor의 구현을 일반 규칙처럼 설명하지 않습니다.
- 측정하지 않은 worst-case latency, power, endurance와 안정성을 단정하지 않습니다.
- 기술·버전 주장은 공식 architecture, project, vendor 자료를 사용하고 URL, release/revision과 확인일을 [공식 자료](reference/sources.md)에 남깁니다.
- 카탈로그의 `owns` 또는 `exit_capabilities`를 바꾸는 설명은 [main 계약 추적표](docs/00-roadmap.md#main-계약-추적표)의 개념·실습·capstone·증거 연결도 함께 갱신합니다.

## 실습을 고칠 때

- 문제의 초기 상태, 입력 사건, 상태 소유자와 완료 조건을 먼저 작성합니다.
- hardware가 없어도 검증 가능한 계약과 실제 board에서만 확인 가능한 계약을 구분합니다.
- timeout, queue overflow, bus error, reset, power loss와 image revert를 정상적인 시험 입력으로 포함합니다.
- 새 계약이나 fixture에는 실행 가능한 starter, 공개 계약을 만족하는 reference와 그 계약 하나를 의도적으로 위반하는 known-wrong을 함께 둡니다.
- checker는 source 모양이 아니라 공개 결과·불변식을 판정하고 `--submission PATH [--json]`을 유지합니다.
- reference는 종료 코드 `0`, starter와 모든 known-wrong은 `1`, 존재하지 않거나 사용할 수 없는 submission은 `2`가 되는지 확인합니다.
- simulator 통과를 실제 timing·electrical·power 보장으로 표현하지 않습니다.

## 코드를 고칠 때

- 작은 결정론적 상태 모델만 `examples/`에 둡니다.
- target-specific code를 추가하면 board, toolchain과 version을 명시합니다.
- build artifact와 generated file은 추적하지 않습니다.
- interrupt context에서 blocking, allocation 또는 긴 formatting을 추가하지 않습니다.
- DMA buffer, persistent record와 update slot의 소유권 전이를 테스트로 드러냅니다.

## evidence와 사람 판정

- 자동 검사 결과에는 실행 명령, 종료 코드, JSON 보고서와 source revision을 남깁니다.
- 설계·운영 판단은 [evidence 템플릿](reference/evidence-template.md)의 질문에 답하고 정상·경계·실패·복구의 raw evidence를 연결합니다.
- 사람이 raw evidence와 설명을 실제로 검토하기 전에는 정확히 `human_review: NOT_TESTED`(미검증)로 기록합니다. checker 통과만으로 이 값을 바꾸거나 자동 PASS 집계에 넣지 않습니다.
- 실제 board 결과에는 board/SoC/device revision, firmware hash, 전원·clock·probe·측정 환경과 오차를 남깁니다. host, simulator, QEMU와 board 결과를 같은 보장으로 합치지 않습니다.
- 로그·dump·trace를 공개하기 전에 credential, provisioning material, device identity와 개인정보를 제거합니다.

## 안전, cleanup과 복구

- host 검증은 network, root 권한, 유료 cloud 자원이나 실제 서비스 변경을 요구하지 않아야 합니다.
- checker나 helper는 전달받은 submission, 학습자 workspace와 raw evidence를 예고 없이 덮어쓰거나 삭제하지 않습니다. 임시 경로를 쓰고 종료 뒤 생성물만 정리합니다.
- 실제 board 실험은 올바른 전압, pin direction, current limit와 isolation을 확인하고 actuator·battery·mains·고온 부하는 별도 안전 절차가 없으면 연결하지 않습니다.
- flash, bootloader, power-cut 또는 update 실험 전에 factory/last-known-good image, calibration·identity 백업과 probe/recovery-mode 진입 절차를 검증합니다.
- 시험 뒤 임시 wiring, 전원, probe, test image와 설정을 정리하고 알려진 정상 상태로 되돌립니다. 복구하지 못했거나 필수 검사를 실행하지 못한 결과를 성공으로 기록하지 않습니다.

## 출처와 라이선스

- Markdown 설명·표·그림은 [CC BY 4.0](LICENSES/CC-BY-4.0.txt), 실행 코드·script·configuration은 [MIT](LICENSES/MIT.txt) 범위로 기여합니다.
- 외부 자료를 가져오면 호환되는 라이선스인지 먼저 확인하고 저작자, 제목, 원본 URL, 라이선스와 수정 여부를 기록합니다. 호환되지 않거나 출처가 불명확한 자료를 복사하지 않습니다.
- 기존 문서를 수정·재배포할 때는 `Seungwoo Kim`, 이 저장소와 branch, CC BY 4.0 링크, 변경 표시를 보존합니다.

## 변경 확인

```sh
./prepare.sh
./verify.sh
make exercises-check
make capstone-check
```

커밋 전에는 다음도 확인합니다.

```sh
git status --short
git diff --check
git diff --staged
```

문서와 해당 상태 모델·검증 변경은 같은 커밋에 둘 수 있습니다. 서로 독립적인 분야 변경은 나누어 기록합니다.
