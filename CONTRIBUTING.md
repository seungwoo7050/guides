# Contributing

`cloud-computing` 변경은 제품 이름보다 책임·상태·실패·비용·검증 계약을 우선합니다. 공급자별 기능은 빠르게 바뀌므로 핵심 문서는 provider-neutral 원리를 소유하고, 특정 서비스의 현재 동작은 공식 문서와 선택 profile에 제한합니다.

## 변경 원칙

- `web-infra`의 Linux·Docker·DNS·TLS·배포 설명을 반복하지 않습니다.
- `distributed-services`의 retry·멱등성 일반론을 복사하지 않고 FaaS event source와 provisioning에 적용합니다.
- `cybersecurity`의 일반 보안 절차를 다시 쓰지 않고 cloud identity·control plane·tenant isolation의 고유 경계를 다룹니다.
- IaaS·PaaS·SaaS는 책임 모델로, FaaS는 serverless 실행 모델로 구분합니다.
- 공급자 마케팅 명칭을 정답으로 고정하지 않습니다. 소비자가 제어하는 층, 공급자가 관리하는 층과 관찰 가능한 계약을 기록합니다.
- 실제 비용을 만드는 예제는 필수 경로에 넣지 않습니다.
- 선택 실험에는 예산, 권한, resource prefix, TTL, inventory와 destroy evidence가 있어야 합니다.

## 문서 변경

각 문서는 다음 중 하나 이상의 질문에 답해야 합니다.

1. 누가 상태와 자원을 소유합니까?
2. 어떤 API·event·시간 경과가 상태를 바꿉니까?
3. 실패하면 어떤 상태가 남습니까?
4. 어떤 책임이 공급자에게 이동하고 무엇이 소비자에게 남습니까?
5. 어떤 증거가 가용성·보안·비용·복구 주장을 지지합니까?
6. 그 증거가 보장하지 않는 것은 무엇입니까?
7. 종료하거나 다른 공급자로 옮길 때 무엇을 추출·삭제·재구성해야 합니까?

공급자별 수치·limit·제품명·동작을 추가할 때는 공식 문서 URL과 확인 날짜를 `docs/90-standards-map.md` 또는 profile 문서에 남깁니다. 시간이 지나면 달라질 수 있는 값을 본문 원리로 일반화하지 않습니다.

## 실습 변경

- 01~06의 template은 의도적으로 검사에 실패해야 합니다.
- reference는 가능한 한 한 가지 답안이 아니라 검토 가능한 근거의 예시로 작성합니다.
- contract는 문장 일치보다 필수 산출물, 구조와 미완성 표시를 검사합니다.
- 07의 local model은 실제 cloud provider를 흉내 내는 emulator가 아닙니다. tenant isolation, event idempotency, quota 원자성, private state와 cleanup 불변식을 결정적으로 검증하는 합성 모델입니다.
- skeleton의 의도한 실패를 없애거나 reference와 동일하게 만들지 않습니다.
- 테스트는 private 구현 모양보다 공개 행동을 검사합니다.

## Capstone 변경

Capstone은 다음 산출물을 함께 요구해야 합니다.

- service classification과 responsibility matrix
- resource inventory와 ownership
- identity·network·data boundary
- failure injection과 recovery evidence
- FaaS event lifecycle 또는 동등한 비동기 처리 계약
- tenant lifecycle과 isolation
- cost·budget·quota
- portability와 exit
- release decision과 residual risk

완성 애플리케이션 코드를 강제하지 않습니다. 문서와 합성 모델만으로도 핵심 판단을 검토할 수 있어야 하며, 실제 provider profile은 선택 확장으로 유지합니다.

## 커밋 구성

권장 흐름은 다음과 같습니다.

```text
chore: establish guide structure and verification
→ docs: define scope, responsibility and evidence model
→ docs: add IaaS and managed platform path
→ docs: add serverless and FaaS path
→ docs: add SaaS tenancy and commercial state path
→ exercise: add document exercises and review references
→ exercise: add deterministic local cloud model
→ docs: add capstone and standards map
→ test: harden negative profiles and source preservation
```

모든 파일을 만든 뒤 의미 없는 커밋으로 사후 분할하지 않습니다. 각 커밋은 가능하면 해당 시점의 구조·링크·reference 검증을 통과해야 합니다.

## 검증

```sh
./prepare.sh
./verify.sh
```

다음 상태가 모두 확인돼야 합니다.

- 문서와 내부 링크가 존재합니다.
- Markdown의 inline·image·reference-style link와 local fragment가 실제 파일·heading을 가리킵니다. 외부 HTTP(S)·`mailto`는 오프라인 필수 검사 범위가 아니므로 공식 출처를 사람이 다시 확인합니다.
- reference 산출물은 계약을 통과합니다.
- 각 template 필수 파일은 의도적인 미완성 표시를 유지하고 정확히 `E_UNFILLED` 때문에 거부됩니다. missing·invalid JSON·checker crash를 의도된 실패로 간주하지 않습니다.
- local model reference는 모든 불변식을 지킵니다.
- vulnerable skeleton과 check별 single-defect mutant는 선언된 ID에서 거부됩니다.
- 준비 뒤 source의 bytes·path·mode가 바뀌거나 symlink가 생기면 검증이 중단됩니다.
- 검증 전후 source와 `.workspace/`의 bytes·path·mode·symlink target 지문이 같습니다.
- 필수 검사는 저장소 밖 임시 복사본에서 실행되며 하나라도 실행되지 않거나 meta-test 수가 기준보다 적으면 실패합니다.
- 검증이 cloud credential이나 외부 서비스에 의존하지 않습니다.

자동 검사는 산출물 구조, 공개 행동, 연결과 결정적 로컬 evidence만 보조 검증합니다. provider의 실제 IAM·가격·billing 지연·region 장애·control plane 의미와 설계 판단은 [`reference/manual-review-guide.md`](reference/manual-review-guide.md)에 따라 사람이 확인합니다.
