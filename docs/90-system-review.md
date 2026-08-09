# 시스템 종합 검토

세 경로를 모두 완료한 뒤 하나의 데이터 제품 또는 capstone을 선택해 다음 높이에서 다시 검토한다. 이 문서는 새로운 개념을 추가하지 않고, 서로 떨어져 보이던 계약이 실제로 연결되는지 확인한다. 카탈로그 소유 범위와 종료 근거의 전체 연결은 [`contract traceability`](../reference/contract-traceability.md)에서 함께 확인한다.

## 1. 업무 의미

- 소비자가 어떤 결정을 내리는가?
- 한 record의 grain은 무엇인가?
- key, event time, update·delete·correction 의미는 무엇인가?
- source of truth와 파생 상태의 owner는 누구인가?

## 2. input과 progress

- bounded input은 어떤 snapshot/manifest로 고정되는가?
- file은 immutable version/checksum/complete marker가 있고 partial·mutable object를 거부하는가?
- API는 stable cursor·cutoff·overlap과 durable raw write 뒤 cursor commit을 사용하는가?
- unbounded input은 어떤 source position으로 재개하는가?
- event-time completeness는 어떻게 추정하는가?
- source와 pipeline delay를 분리할 수 있는가?

## 3. schema와 판본

- writer/reader 판본 범위는 무엇인가?
- historical data를 새 reader가 읽는가?
- semantic change를 schema compatibility 외에 어떻게 검증하는가?
- state/table schema upgrade와 rollback을 시험했는가?
- old/new output을 같은 source cutoff로 대사하고 consumer별 cutover·deprecation을 추적하는가?

## 4. transform

- 같은 input과 version에서 logical output이 결정적인가?
- partition·shuffle·join cardinality와 skew를 측정했는가?
- reference data/as-of version을 고정했는가?
- batch와 stream이 같은 grain/time/correction 규칙을 사용하는가?

## 5. state와 delivery

- job·run·task attempt·output version과 상태 전이가 run ledger에 분리돼 있는가?
- state key와 lifetime은 무엇인가?
- checkpoint가 source·operator·sink 어느 경계를 포함하는가?
- duplicate, stale event와 retry를 어떤 ID/version으로 처리하는가?
- exactly-once 주장은 어느 outcome boundary에 한정되는가?
- conflicting identity가 arrival order로 승인되지 않고 sticky quarantine에 남는가?

## 6. storage와 publish

- staging과 published snapshot이 분리돼 있는가?
- validation 실패 때 이전 정상 snapshot이 유지되는가?
- table/file/catalog commit과 orphan cleanup을 설명할 수 있는가?
- partition/file layout이 실제 query와 retention에 맞는가?

## 7. replay와 correction

- late data와 correction window는 무엇인가?
- backfill의 interval·input·code·reference version을 고정하는가?
- live와 backfill resource/output을 격리하는가?
- rollback과 downstream propagation을 수행할 수 있는가?

## 8. evidence

- source coverage와 sink snapshot을 대사하는가?
- key·count·aggregate·sample diff가 있는가?
- quality가 publish를 실제로 gate하는가?
- run-level lineage로 input, code와 output을 연결하는가?
- consumer가 freshness와 finality를 읽을 수 있는가?
- source delay, pipeline delay와 oldest backlog를 분리하는가?
- run/dataset별 unit cost와 retry·backfill·compaction waste를 귀속하는가?
- quarantine rule/version, repair run과 secure disposition을 추적하는가?

## 9. 운영

- retryable/non-retryable/unknown failure를 구분하는가?
- timeout 뒤 외부 job과 staging 상태를 조사하는가?
- alert가 영향 dataset/interval/consumer와 runbook을 제공하는가?
- source retention 초과, catalog failure와 compaction conflict를 복구할 수 있는가?
- source→operator→sink backpressure 경로, retry storm과 backlog recovery 시간을 계산하는가?

## 10. governance

- 필요한 최소 field만 capture하는가?
- raw·derived·log·quarantine·backup의 classification과 retention이 있는가?
- workload identity와 write/commit 권한이 분리돼 있는가?
- 삭제와 legal hold가 lineage를 따라 전파되는가?
- quarantine이 원본 classification·최소 권한·audit·retention을 유지하는가?
- repair 또는 deletion 뒤 old snapshot·derived output·backup의 잔존을 검증하는가?

## 11. release와 consumer cutover

- code/runtime/config/schema/input/reference/state version을 하나의 release evidence로 고정하는가?
- old/new reader·writer·state·table·consumer matrix를 실행했는가?
- shadow/dual output은 같은 source cutoff로 key·aggregate·sample을 비교하는가?
- canary consumer가 실제 schema, volume, late correction, query와 access pattern을 대표하는가?
- consumer inventory에 migration sign-off, deprecation deadline와 last verified read가 있는가?
- rollback과 roll-forward가 dataset pointer뿐 아니라 downstream materialization·cache·deletion까지 다루는가?

## 검토 evidence와 한계

Repository 검증은 문서 구조, reference와 skeleton의 공개 계약, capstone artifact 형식을 확인할 수 있다. 다음은 선택한 runtime과 사람 검토가 필요하다.

- 실제 pipeline fixture와 failure injection 결과
- source/sink snapshot, checkpoint, log position과 reconciliation report
- backpressure·capacity·freshness·cost 측정
- consumer별 semantic sign-off와 cutover rehearsal
- access·quarantine·retention·deletion propagation evidence
- 선택하지 않은 broker, engine, table format과 대규모 운영에서 아직 보장하지 않는 범위

자동 검사가 통과했다는 사실을 교육적 완성이나 production 보장으로 해석하지 않는다.

## 최종 설명 과제

다음 문장을 구체적인 자신의 시스템으로 완성한다.

> 이 데이터 제품은 ______를 한 record로 보고 ______를 stable identity로 사용한다. 업무 시간은 ______이며 source progress는 ______로 추적한다. 동일 입력의 재실행은 ______ publish 계약으로 같은 논리 결과를 만든다. late/corrected data는 ______까지 ______ 방식으로 반영한다. consumer는 ______ quality와 ______ freshness를 통해 결과를 신뢰하며, 문제가 발생하면 ______ snapshot으로 rollback하고 ______ reconciliation으로 복구를 증명한다.

## 종료 기준

- 위 질문에 도구 이름이 아니라 상태·책임·실패·증거로 답한다.
- 한 failure를 source, ingestion, transform, state, storage, publish, consumer 계층으로 분리한다.
- 빠른 정상 경로뿐 아니라 restart, partial publish, late correction, schema change와 backfill을 같은 설계에 포함한다.
- 아직 구현하지 않은 보장과 실제 플랫폼에서 추가 검증해야 할 항목을 명시한다.
- 다섯 `owns`와 세 `exit_capabilities`의 실제 근거를 [`contract traceability`](../reference/contract-traceability.md)에서 찾아 자신의 artifact로 대체한다.
