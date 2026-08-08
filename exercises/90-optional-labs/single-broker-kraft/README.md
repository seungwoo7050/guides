# 선택 실습: 단일 브로커 KRaft의 내부 토픽 설정

## 목표


이 실습은 분산 서비스의 핵심 설계가 아니라 **로컬 단일 브로커 실습 환경을 올바르게 준비하는 방법**을 다룹니다. 따라서 본 과정의 마지막 선택 실습으로 분리되어 있습니다.

Kafka 브로커 프로세스가 실행 중이고 일반 토픽을 만들 수 있어도 consumer group은 `__consumer_offsets` 내부 토픽을 필요로 합니다. 단일 브로커에서 내부 토픽 복제 수를 3으로 두면 브로커의 healthcheck가 성공한 뒤에도 group consumer는 동작하지 않을 수 있습니다.

## 비교할 구성

`skeleton/compose.yaml`은 다음과 같이 잘못된 단일 브로커 구성을 사용합니다.

```text
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=3
KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=3
KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=2
```

`reference/compose.yaml`은 학습용 단일 브로커라는 제한을 명시하고 모두 1로 맞춥니다. 운영 클러스터에서도 복제 수를 1로 사용하라는 뜻이 아닙니다.

## 완료 기준

- direct partition consumer가 두 구성에서 모두 같은 메시지를 읽어 broker 기본 동작을 증명합니다.
- skeleton의 group consumer만 내부 토픽 복제 계약 때문에 실패하고 reference는 성공합니다.
- 검증 뒤 해당 실행의 container·network·volume만 사라지고 다른 Docker 자원은 유지됩니다.

## 자기 설명

- direct consumer 성공을 먼저 확인해야 group consumer 실패 원인을 특정할 수 있는 이유는 무엇입니까?
- replication factor 1이 단일 broker 학습 환경에만 적합한 이유는 무엇입니까?

## 검증

저장소 루트에서 `./prepare.sh`가 Kafka 이미지를 준비한 뒤 다음 명령을 실행할 수 있습니다.

```sh
./exercises/90-optional-labs/single-broker-kraft/verify.sh
```

검사기는 두 구성을 순서대로 시작합니다.

1. broker API가 응답하는지 확인합니다.
2. 일반 토픽을 만들고 메시지를 한 건 보냅니다.
3. partition과 offset을 직접 지정한 consumer가 같은 메시지를 읽어 broker 기본 경로를 증명합니다.
4. 명시적인 group ID를 가진 consumer를 별도로 실행합니다.
5. skeleton에서는 group consumer만 지정된 내부 토픽 복제 오류로 실패해야 합니다.
6. reference에서는 group consumer도 같은 메시지를 읽어야 합니다.
7. 모든 컨테이너·네트워크·볼륨을 정리합니다.

`./exercises/90-optional-labs/single-broker-kraft/verify.sh --static`은 Docker를 시작하지 않고 두 설정의 핵심 값과 Compose 문법만 확인합니다.

## 제한

이 실습은 다음을 검증하지 않습니다.

- 여러 브로커 장애 허용
- controller quorum의 고가용성
- 운영 보안과 인증
- 디스크 보존·복제 성능
- 운영 클러스터의 적절한 replication factor

그 영역은 실제 클러스터 요구사항과 [`web-infra`](https://github.com/seungwoo7050/guides/tree/web-infra)의 운영 경계를 함께 검토해야 합니다.
