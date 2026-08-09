# 분산 시스템 1차 자료 읽기 양식

## Source identity

```text
title:
authors:
publication/version:
stable URL:
implementation or artifact:
```

## System model

- node와 process:
- communication:
- storage:
- clock/time:
- membership:

## Failure model

- 허용하는 fault:
- 허용하지 않는 fault:
- 진행에 필요한 synchrony/fairness:

## Specification

- sequential 또는 abstract state:
- safety:
- liveness:
- consistency:

## Protocol state

- durable state:
- volatile state:
- message:
- timer:
- recovery state:

## 핵심 invariant와 proof 구조

- invariant:
- induction 또는 contradiction 지점:
- quorum/intersection 사용 지점:
- time assumption 사용 지점:

## 구현으로 옮길 때 추가되는 것

- serialization/storage boundary:
- retry/session:
- snapshot/compaction:
- membership/upgrade:
- observability:
- corruption handling:

## 다루지 않는 운영 문제

- 성능:
- 배포와 호환성:
- 보안:
- operator intervention:

## 재현 과제

- 최소 trace:
- fault schedule:
- checker/invariant:
- 예상하지 못한 결과:
