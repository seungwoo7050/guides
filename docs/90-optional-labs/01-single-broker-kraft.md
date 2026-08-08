# 선택 실습: 단일 브로커 KRaft의 내부 토픽

## 목표

단일 Kafka 브로커를 로컬에서 실행할 때 내부 토픽의 복제 계수를 클러스터 크기와 맞추지 않으면 producer 연결만 보고 정상이라고 오판할 수 있음을 확인합니다.

## 범위

이 실습은 분산 서비스 설계의 핵심 경로가 아니라 Kafka 로컬 환경의 설정 실습입니다. Kafka 운영, 보안, 복제와 장애 조치를 전체적으로 설명하지 않습니다.

Docker와 Docker Compose v2가 필요합니다. 저장소의 필수 `verify.sh`는 구성 파일을 항상 정적으로 검사하고, Docker를 사용할 수 있으며 `prepare.sh`가 이미지를 준비한 환경에서만 실제 통합 검사를 실행합니다.

## 문제

단일 broker인데 consumer group이 사용하는 내부 토픽의 복제 계수를 3으로 두면 내부 토픽을 만들 수 없습니다. broker process가 실행 중이고 일반 topic을 나열할 수 있어도 group 기반 소비가 실패할 수 있습니다.

단일 broker 로컬 환경에서는 다음 값을 1로 맞춥니다.

```text
offsets topic replication factor
transaction state log replication factor
transaction state log minimum ISR
```

운영 다중 broker 환경의 권장 복제 설계를 단일 로컬 환경에 그대로 적용하거나, 반대로 단일 broker 설정을 운영에 사용하는 것은 모두 잘못입니다.

## 실습

[실습 README](../../exercises/90-optional-labs/single-broker-kraft/README.md)의 broken 구성과 reference 구성을 비교합니다.

## 완료 조건

- process health와 consumer group 기능을 별도로 검사합니다.
- 단일 broker용 내부 토픽 설정의 이유를 설명할 수 있습니다.
- 로컬 편의 설정을 운영 권장값으로 일반화하지 않습니다.
