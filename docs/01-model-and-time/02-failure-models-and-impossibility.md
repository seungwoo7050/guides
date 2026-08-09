# Failure model, 비동기성과 불가능성

## 목표

분산 알고리즘이 허용하는 장애와 시간 가정을 먼저 명시하고, 그 가정 아래 가능한 safety와 liveness를 구분합니다. FLP와 CAP를 “분산 시스템은 불가능하다”는 문구가 아니라 설계 경계를 판단하는 도구로 사용합니다.

## Failure model을 먼저 씁니다

같은 protocol이라도 어떤 장애를 허용하는지에 따라 보장 범위가 달라집니다.

### Crash-stop

node가 중단하면 다시 돌아오지 않습니다. 다른 node는 crash를 직접 관찰하지 못하고 통신 부재만 봅니다.

이 모델은 알고리즘의 기본 safety를 설명하기 쉽지만 실제 서비스의 restart와 disk recovery를 충분히 표현하지 못합니다.

### Crash-recovery

node가 중단했다가 durable state를 읽어 다시 참여합니다.

명시할 항목:

- crash 전에 어떤 write가 durable했는가
- restart할 때 어떤 volatile state를 초기화하는가
- 오래된 message가 restart 뒤 도착할 수 있는가
- 같은 node ID와 incarnation을 어떻게 구분하는가

Raft capstone은 crash-recovery를 기본 모델로 사용합니다.

### Omission과 partition

send·receive 또는 특정 link의 message가 유실됩니다. partition은 일정 기간 node 집합 사이의 통신이 불가능하거나 극단적으로 지연되는 실행으로 모델링합니다.

partition은 대칭일 필요가 없습니다.

```text
A -> B 차단
B -> A 전달 가능
```

방향성 장애는 heartbeat와 acknowledgment가 서로 다른 경로를 사용할 때 중요합니다.

### Byzantine

node가 임의의 message를 만들거나 거짓말하고 protocol을 위반합니다. 이 가이드의 핵심 알고리즘은 crash·omission 장애를 대상으로 하며 Byzantine fault tolerance를 제공하지 않습니다.

TLS, 인증과 message integrity를 적용해도 정상 node의 software bug나 compromised key가 만드는 Byzantine behavior가 자동으로 해결되는 것은 아닙니다.

## 시간 모델

### Synchronous

message와 처리 시간이 알려진 상한 안에 있다고 가정합니다. 상한이 정확하면 timeout으로 실패를 판정하고 round 기반 진행을 설계할 수 있습니다.

실제 범용 network에서는 항상 성립한다고 보기 어렵습니다.

### Asynchronous

message 지연, 처리 시간과 clock drift에 알려진 상한이 없습니다. message는 결국 도착할 수도 있지만 언제인지 알 수 없습니다.

이 모델에서는 느린 node와 crash한 node를 유한한 관찰만으로 확정적으로 구분할 수 없습니다.

### Partial synchrony

일정 시점 이후 알려지거나 알려지지 않은 bound가 성립한다고 가정합니다. 실용 consensus algorithm은 safety를 항상 유지하고, network가 충분히 안정된 기간에는 liveness를 얻는 방식으로 설명하는 경우가 많습니다.

설계 문서에는 “eventually synchronous” 같은 표현만 적지 말고 liveness에 필요한 실제 조건을 씁니다.

```text
- 과반수 node가 실행 중입니다.
- 과반수 사이의 message가 election timeout보다 빠르게 왕복합니다.
- timer가 계속 실행됩니다.
- storage operation이 완료됩니다.
- client가 현재 leader 또는 redirect 경로에 도달합니다.
```

## Consensus 명세

간단한 consensus 문제는 다음 속성을 가집니다.

- **agreement**: 올바른 participant가 서로 다른 값을 결정하지 않습니다.
- **validity**: 결정 값은 허용된 proposal과 관련된 값입니다.
- **integrity**: 한 participant가 여러 값을 결정하지 않습니다.
- **termination**: 조건을 만족하는 실행에서 올바른 participant가 결국 결정합니다.

앞의 세 항목은 주로 safety이고 termination은 liveness입니다.

## FLP를 정확히 읽습니다

FLP 결과는 완전 비동기 message-passing system에서 deterministic consensus protocol이 한 process의 crash 가능성만 있어도 **모든 admissible execution에서 termination을 보장할 수 없음**을 보입니다.

이 결과가 말하지 않는 것:

- consensus safety가 불가능하다는 뜻이 아닙니다.
- 모든 실행이 영원히 멈춘다는 뜻이 아닙니다.
- randomization, failure detector나 partial synchrony를 사용할 수 없다는 뜻이 아닙니다.
- 실제 Raft cluster가 절대 leader를 선출하지 못한다는 뜻이 아닙니다.

실용 protocol은 보통 다음 방식으로 경계를 바꿉니다.

- randomized election timeout
- network가 안정되는 기간에 대한 partial synchrony 가정
- majority availability
- failure detector의 의심 결과 사용

중요한 것은 safety를 timeout 추측에 의존시키지 않고, liveness만 시간 가정에 의존시키는 것입니다.

## CAP를 정확히 읽습니다

network partition이 발생한 실행에서 linearizable consistency와 availability를 동시에 모두 보장할 수 없다는 경계로 사용합니다.

여기서 availability는 단순히 “서비스 uptime이 높다”가 아니라 **partition되지 않은 각 non-failing node가 받은 요청에 최종 응답을 제공하는 성질**에 가깝습니다. consistency도 모든 종류의 consistency가 아니라 atomic 또는 linearizable register에 해당하는 강한 의미입니다.

따라서 다음 표현은 부정확합니다.

- “분산 시스템은 C, A, P 중 두 개만 고릅니다.”
- “latency가 높으면 CAP에서 availability를 잃었습니다.”
- “eventual consistency를 쓰면 partition이 사라집니다.”

설계 질문은 더 구체적이어야 합니다.

```text
partition 중 어느 side가 write를 받습니까?
거절·timeout·stale read 중 어떤 응답을 허용합니까?
partition이 끝난 뒤 conflict를 누가 어떤 규칙으로 해결합니까?
client session에 read-your-writes를 제공합니까?
```

## Failure budget과 fault threshold

`N`개 replica가 있을 때 몇 개의 failure를 견디는지는 protocol과 quorum 규칙에 따라 다릅니다.

- majority consensus group은 보통 `N = 2f + 1`에서 `f`개 crash를 견디며 진행합니다.
- Byzantine consensus는 더 강한 가정과 더 많은 replica가 필요합니다.
- replica 수가 충분해도 같은 power, zone, control plane에 묶여 있으면 독립 failure가 아닐 수 있습니다.

숫자만 적지 말고 failure domain을 함께 적습니다.

## 설계 기록 형식

각 protocol 문서에 다음 표를 둡니다.

| 항목 | 질문 |
|---|---|
| Participants | 누가 protocol state를 가집니까? |
| Network | delay·loss·duplicate·reorder·partition을 허용합니까? |
| Failure | crash-stop, crash-recovery, omission, Byzantine 중 무엇입니까? |
| Storage | 어떤 update가 durable하며 torn write를 허용합니까? |
| Time | safety와 liveness가 각각 어떤 clock·bound에 의존합니까? |
| Threshold | 몇 개의 failure와 어떤 failure domain을 허용합니까? |
| Safety | 어떤 상태가 절대 발생하면 안 됩니까? |
| Liveness | 어떤 조건에서 무엇이 결국 완료됩니까? |

## 실패 조건

- crash-recovery 구현을 설명하면서 durable state를 나열하지 않습니다.
- timeout 값을 조정하면 split brain safety가 해결된다고 봅니다.
- FLP를 이유로 consensus 구현 검증을 포기합니다.
- CAP를 일반적인 성능·가용성 trade-off 문구로 사용합니다.
- majority 수만 맞으면 replica failure가 독립이라고 가정합니다.
- Byzantine 가능성을 언급하면서 인증·key compromise·임의 state mutation을 모델링하지 않습니다.

## 검증

[failure model 실습](../../exercises/01-model-and-time/02-failure-model/README.md)은 같은 protocol 설명을 crash-stop, crash-recovery와 partition 모델에 각각 적용해 보장 범위가 어떻게 달라지는지 기록합니다.

검사할 핵심은 “장애가 발생해도 성공한다”가 아닙니다.

1. 허용한 장애가 실제 fixture에 포함되어 있습니다.
2. safety는 모든 생성 trace에서 유지됩니다.
3. liveness 실패 trace가 시간 가정 위반으로 설명됩니다.
4. 모델 밖 장애를 지원한다고 주장하지 않습니다.

## 완료 조건

- crash-stop, crash-recovery, omission, partition과 Byzantine model을 구분합니다.
- timeout이 확정 failure evidence가 아님을 설명합니다.
- safety와 liveness가 의존하는 가정을 따로 적습니다.
- FLP와 CAP가 제한하는 속성을 과장하지 않습니다.
- replica 수와 failure domain을 함께 검토합니다.
