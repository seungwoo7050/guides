# Data Engineering Guide

여러 원천의 데이터를 **계약 가능한 record**, **재실행 가능한 batch**, **event time을 보존하는 stream**, **복구 가능한 CDC와 backfill**, **관찰 가능한 데이터 제품**으로 전달하는 과정을 학습하는 가이드다.

이 저장소는 Spark, Kafka, Airflow, dbt, Iceberg 같은 제품의 사용법을 순서대로 나열하지 않는다. 도구가 달라져도 유지되는 데이터 상태와 실패 계약을 먼저 다룬다.

```text
원천의 사실
→ 식별자·시간·schema 계약
→ batch 또는 stream 변환
→ 검증된 publish
→ 품질·freshness·lineage 근거
→ correction·backfill·replay
```

## 시작

```bash
make prepare
make check
make verify
make clean
```

- `make prepare`는 Python 3.11 이상과 필수 도구를 확인하고 전체 구조를 검사한 뒤, HEAD·Git index·source·도구 identity를 담은 mode `0600` marker를 원자적으로 기록한다. source와 learner workspace는 바꾸지 않는다.
- `make check`는 네트워크와 외부 서비스 없이 문서·내부 링크·예제, reference·starter·known-wrong 계약과 준비·검증·정리·workspace 안전 회귀를 검사한다.
- `make verify`는 현재 marker를 확인하고 저장소 밖 배타 로그와 격리 복사본에서 필수 검사를 모두 실행한다. 성공·실패 모두에서 source, learner workspace, Git index와 HEAD가 보존되는지 확인한다.
- `make clean`은 `.guide`와 가이드가 만든 cache만 제거하고 learner workspace는 보존한다.
- `VERIFY_LOG`는 저장소 밖의 아직 존재하지 않는 절대 경로만 허용한다. 생략하면 충돌 없는 임시 로그를 만든다.

## 자료 지도

- 학습 순서와 세 경로: [`docs/00-roadmap.md`](docs/00-roadmap.md)
- 작은 실행 모델과 대응 실습: [`examples/README.md`](examples/README.md)
- 정본 계약의 구현 근거: [`reference/contract-traceability.md`](reference/contract-traceability.md)
- 두 로컬 초안의 보존·통합 결정과 교차 경로 확장: [`reference/draft-integration.md`](reference/draft-integration.md)
- 최신 구현 검토용 공식 자료: [`reference/official-sources.md`](reference/official-sources.md)
- 변경·라이선스·안전 규칙: [`CONTRIBUTING.md`](CONTRIBUTING.md), [`LICENSE.md`](LICENSE.md)

## 세 학습 경로

### 분석 데이터 제품 경로

데이터 계약 → 분석 모델·역사 → replay-safe batch → partition·join → columnar layout → orchestration → 품질·lineage → batch capstone

완료 뒤에는 원천 snapshot과 data interval을 고정하고, 같은 입력의 재실행이 같은 논리 결과를 만들며, 소비자가 freshness와 품질을 판단할 수 있는 batch 데이터 제품을 설계할 수 있어야 한다.

### 스트림 처리 경로

데이터 계약 → event time → window·watermark·trigger → keyed state·dedup → correction → stream capstone

완료 뒤에는 processing time과 event time을 분리하고, out-of-order·late event·duplicate·restart를 정상 입력으로 다루며, 결과의 잠정성과 수정 가능성을 명시할 수 있어야 한다.

### CDC와 데이터 플랫폼 경로

데이터 계약 → snapshot+log position → CDC merge → table format·snapshot → compaction → orchestration·backfill·reconciliation → CDC capstone

완료 뒤에는 snapshot과 변경 로그 사이의 틈을 없애고, schema·delete·transaction 경계를 보존하며, 장애 뒤 재개·재처리·대사 가능한 데이터 흐름을 설계할 수 있어야 한다.

## 선행지식과 경계

필수 기반은 다음이다.

- [`python`](https://github.com/seungwoo7050/guides/tree/python): 표준 라이브러리로 record·파일·CLI·테스트를 다루는 능력
- [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems): 관계 의미, transaction, index와 migration의 기본 계약

다음은 권장 기반이다.

- [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services): 중복 전달, 순서 역전, Outbox와 재조정
- [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems): source log·복제·partition·순서 보장의 시스템 경계를 구분하는 능력

이 브랜치는 다음을 다시 소유하지 않는다.

- DBMS 페이지·MVCC·WAL과 질의 실행기: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- 서비스 업무 상태의 Outbox·Saga·보상: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- 합의·replicated log·sharding 알고리즘: [`distributed-systems`](https://github.com/seungwoo7050/guides/tree/distributed-systems)
- 모델 학습·평가·fine-tuning: [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)
- Kubernetes와 다중 팀 self-service 플랫폼: [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)

## 연결과 다음 경로

- 분석·학습 소비자에게 데이터 제품을 전달하는 경계는 [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning)과 연결한다. 이 가이드는 model artifact를 만들지 않고 입력 dataset의 의미·판본·품질 근거까지만 책임진다.
- 여러 팀에 pipeline 실행·관측·정책 경로를 제공하는 다음 심화는 [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)이다. 이 가이드에서는 개별 데이터 제품의 orchestration 계약까지만 구현한다.
- 정본 업무 경로는 `git → python → database-systems → data-engineering`이며, 게임 데이터·ML 경로에서는 `database-systems → data-engineering → machine-learning` 순서로 연결된다.

## 작업 공간

구현 연습의 `skeleton/`은 직접 수정하지 않고 workspace를 만든다.

```bash
./scripts/new-workspace.sh exercises/02-batch-processing/01-replay-safe-batch
./scripts/check-workspace.sh exercises/02-batch-processing/01-replay-safe-batch
```

workspace 도구는 manifest에 등록된 exercise만 허용하고 경로 탈출·symlink·특수 파일을 거부한다. lock과 sibling staging을 사용해 mode와 bytes를 확인한 뒤 macOS/Linux의 native no-replace rename으로 한 번만 publish하므로 기존 workspace를 덮어쓰지 않는다. 충돌·실패·중단 때는 자신이 만든 staging과 lock만 정리한다. 초기 workspace는 의도한 학습 계약에서 실패하며, 구현 뒤 같은 검사 명령이 통과해야 완료다.

Capstone은 완성 코드를 제공하지 않는다. 대신 입력·상태·실패·산출물·검증 rubric을 제공하며, 학습자가 구현 기술을 선택한다.

## 종료 능력

전체 경로를 완료하면 다음을 할 수 있어야 한다.

- record의 grain·identity·event time·correction 계약을 문서화한다.
- batch와 stream의 재실행·중복·late data·부분 publish 실패를 구분한다.
- CDC snapshot과 log position을 연결하고 delete·schema change를 보존한다.
- partition·columnar layout·compaction을 질의와 운영 비용의 trade-off로 설명한다.
- backfill과 replay를 정상 운영 절차로 설계하고 source/sink 대사로 결과를 증명한다.
- freshness·completeness·uniqueness·lineage와 incident 근거를 데이터 제품 계약에 포함한다.

이 근거는 특정 상용 플랫폼의 운영 숙련이나 대규모 cluster의 성능을 자동으로 증명하지 않는다. 실제 제품에서는 해당 engine과 조직의 권한·비용·용량 제약을 추가로 검증해야 한다.
