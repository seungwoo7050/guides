# Consensus와 leader election

## 목표

여러 node가 하나의 값 또는 log prefix에 합의해야 하는 이유를 이해하고, leader election을 단순한 heartbeat 기반 장애 판정이 아니라 **term·vote·quorum으로 권한을 증명하는 protocol**로 모델링합니다.

## Consensus가 필요한 지점

분산 시스템에서 여러 participant가 다음 중 하나를 선택해야 할 때 consensus 문제가 나타납니다.

- 다음 configuration 또는 leader
- replicated log의 다음 command
- shard의 authoritative owner
- transaction의 결정 기록
- metadata version

leader를 선출하는 목적도 “한 node를 master라고 부르기”가 아니라 **어떤 명령 순서를 제안할 권한이 있는지 다른 node가 같은 epoch에 대해 동의하도록 만드는 것**입니다.

## Consensus 속성

간단한 single-decree consensus는 다음을 요구합니다.

- agreement: 서로 다른 값을 결정하지 않습니다.
- validity: 결정 값이 허용된 proposal과 연결됩니다.
- integrity: participant가 여러 값을 결정하지 않습니다.
- termination: 필요한 환경 조건에서 결국 결정합니다.

replicated log는 이 결정을 index마다 반복하거나 하나의 leader epoch 안에서 여러 entry로 확장합니다.

## Term과 epoch

Raft는 증가하는 `term`으로 election과 leadership generation을 구분합니다.

```text
term 8: A leader
term 9: B leader
term 10: election in progress
```

term은 wall clock이 아닙니다. 더 큰 term을 관찰하면 local node는 이전 leadership 주장을 버리고 follower로 전환합니다.

term의 역할:

- 오래된 leader message를 식별합니다.
- vote가 어느 election에 속하는지 구분합니다.
- log entry의 생성 epoch를 기록합니다.
- commit safety를 판단하는 근거가 됩니다.

term이 증가한다고 새 leader가 자동으로 존재하는 것은 아닙니다.

## Election timeout과 candidate

follower가 일정 기간 valid leader contact를 받지 못하면 candidate가 될 수 있습니다.

```text
1. currentTerm을 증가합니다.
2. 자신에게 vote합니다.
3. durable term과 votedFor를 저장합니다.
4. 다른 voter에 RequestVote를 보냅니다.
5. current term의 majority를 얻으면 leader가 됩니다.
```

randomized election timeout은 여러 follower가 동시에 candidate가 되는 확률을 줄여 liveness를 돕습니다. safety는 random timeout에 의존하면 안 됩니다.

## Vote 조건

voter는 한 term에 최대 한 candidate에게 vote합니다. 또한 candidate의 log가 voter보다 충분히 up-to-date한지 확인합니다.

일반적인 Raft 비교:

```text
candidate lastLogTerm > voter lastLogTerm
또는
lastLogTerm이 같고 candidate lastLogIndex >= voter lastLogIndex
```

이 조건은 committed entry가 없는 candidate가 미래 leader가 되는 것을 막는 leader completeness의 일부입니다.

단순히 candidate ID나 log 길이만 비교하면 term이 더 오래된 긴 uncommitted suffix를 가진 node가 안전한 candidate를 이길 수 있습니다.

## Majority와 election safety

한 term에 두 candidate가 각각 majority vote를 받으려면 두 quorum이 적어도 한 voter에서 교차합니다. 한 voter가 같은 term에 한 번만 vote한다면 둘 다 majority를 얻을 수 없습니다.

```text
N = 5
majority = 3
어떤 두 3-node set도 최소 한 node에서 교차합니다.
```

이 argument는 membership이 고정되어 있다는 전제가 있습니다. configuration을 잘못 바꾸면 서로 교차하지 않는 old/new majority가 생길 수 있습니다.

## Higher term 처리

node가 request 또는 response에서 더 큰 term을 보면 다음을 수행합니다.

```text
currentTerm = higherTerm
role = follower
votedFor = none
진행 중인 leader 작업과 lease 주장을 종료
```

단, `votedFor` 초기화와 term persistence 순서를 명시해야 합니다. crash 후 이전 term으로 돌아가면 같은 logical term에 여러 vote를 줄 수 있습니다.

## Split vote와 재선거

여러 candidate가 vote를 나누면 누구도 majority를 얻지 못합니다. 새로운 timeout에서 더 큰 term으로 다시 시도합니다.

liveness 조건:

- majority가 서로 통신할 수 있습니다.
- 적어도 한 candidate가 다른 candidate보다 충분히 먼저 timeout됩니다.
- message와 storage operation이 안정 기간 안에 완료됩니다.

고정된 동일 timeout을 모든 node에 사용하면 반복 split vote가 생길 수 있습니다.

## Pre-vote와 disruption 방지

오래 partition되었던 node가 돌아와 무조건 term을 증가시키면 정상 leader를 불필요하게 step down시킬 수 있습니다. pre-vote는 실제 term 증가 전에 majority contact 가능성과 log freshness를 확인하는 확장입니다.

pre-vote도 정확한 failure 판정을 제공하지 않습니다. 불필요한 disruption을 줄이는 liveness optimization이며 core safety invariant를 대체하지 않습니다.

## Leader 권한의 한계

leader가 선출되었다고 다음이 자동으로 보장되지 않습니다.

- 모든 follower가 즉시 leader를 압니다.
- old leader가 모든 client request를 즉시 거절합니다.
- leader local state가 최신 apply state입니다.
- follower read가 최신입니다.
- external resource에 대한 exclusive ownership이 있습니다.

외부 resource에는 term 또는 monotonic fencing token을 함께 전달해 오래된 leader의 write를 거절해야 합니다.

## Paxos, Viewstamped Replication과 Raft

여러 consensus family가 있지만 이 가이드는 capstone의 구현 언어로 Raft를 선택합니다. 이유는 election, log replication, persistence, snapshot과 membership을 하나의 학습 가능한 state model로 연결하기 쉽기 때문입니다.

이는 Raft가 모든 환경에서 더 우수하거나 Paxos와 Viewstamped Replication을 배울 필요가 없다는 뜻이 아닙니다. 선택 경로에서 다른 protocol의 state와 proof structure를 비교합니다.

## 실패 조건

- heartbeat timeout을 crash의 확정 증거로 사용합니다.
- term과 vote를 durable하게 저장하기 전에 vote response를 보냅니다.
- 한 term에 여러 candidate에게 vote할 수 있습니다.
- candidate log freshness를 log 길이만으로 판단합니다.
- 더 큰 term을 본 leader가 기존 request를 계속 commit합니다.
- membership 변경 중 old/new quorum 교차를 확인하지 않습니다.
- leader identity만으로 외부 resource write 권한을 증명합니다.

## 검증

[election trace 실습](../../exercises/03-consensus-and-membership/01-election-trace/README.md)은 delay, split vote, crash와 restart가 포함된 event를 제공합니다.

반드시 검사할 trace:

1. 두 candidate가 같은 term에서 vote를 나눕니다.
2. voter가 vote를 저장한 직후 crash합니다.
3. restart 뒤 같은 term의 다른 candidate가 요청합니다.
4. stale log candidate와 shorter but newer-term candidate가 경쟁합니다.
5. old leader가 partition 뒤 더 큰 term message를 받습니다.

부정 불변식:

```text
같은 term에 leader가 둘 존재하지 않습니다.
같은 voter가 같은 term에 두 candidate를 지지하지 않습니다.
committed entry를 잃은 candidate가 leader가 되지 않습니다.
```

## 완료 조건

- consensus와 단순 coordinator 선택을 구분합니다.
- term, durable vote와 quorum 교차로 election safety를 설명합니다.
- election timeout이 liveness 도구임을 이해합니다.
- log freshness가 leader completeness에 연결되는 이유를 설명합니다.
- higher term과 external fencing을 올바르게 처리합니다.
