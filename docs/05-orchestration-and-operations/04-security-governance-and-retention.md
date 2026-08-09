# 보안, governance와 retention

## 학습 목표

- data classification, 최소 수집, 목적 제한과 retention을 pipeline 설계에 포함한다.
- raw·derived·backup·log·quarantine에 흩어진 sensitive data의 lifecycle을 추적한다.
- service identity와 row/column/domain access를 데이터 경계에 적용한다.
- 삭제·legal hold·audit 요구를 snapshot과 lineage 운영에 연결한다.

## 범위

인증, 암호, 위협 모델과 incident response의 일반 원리는 `cybersecurity`와 `web-infra`가 소유한다. 이 문서는 **데이터가 여러 pipeline과 derived dataset으로 복제되는 과정에서 어떤 계약을 추가해야 하는가**를 다룬다.

## 핵심 모델

```text
수집 목적
→ 분류와 최소 field
→ 전송·저장·처리 권한
→ derived propagation
→ 접근·사용 audit
→ retention·삭제·legal hold
→ 복구와 증명
```

storage encryption만으로 governance가 완성되지 않는다.

## data classification

예시 분류:

- public
- internal
- confidential
- restricted/regulated

실제 조직 용어를 사용한다. dataset 단위만으로 부족할 수 있다. 같은 table 안에서도 email, IP, financial identifier와 aggregate가 다른 등급일 수 있다.

metadata에 포함할 것:

- classification
- sensitive fields와 이유
- owner/steward
- approved purposes
- allowed consumer domains
- retention
- masking/tokenization
- deletion propagation

## 최소 수집과 목적 제한

CDC에서 source table 전체를 capture하기보다 필요한 column과 table만 선택한다. “나중에 쓸 수 있음”은 무제한 복제 근거가 아니다.

질문:

- consumer 결정에 꼭 필요한 field인가?
- raw 보존 없이 source에서 다시 얻을 수 있는가?
- pseudonymized key로 충분한가?
- precise timestamp/location이 필요한가?
- debug payload가 production dataset에 남는가?

field를 줄이면 breach impact, retention과 schema coordination도 줄어든다.

## identity와 access

### workload identity

pipeline/job마다 독립 identity를 사용하고 사람의 장기 credential을 공유하지 않는다.

### least privilege

- source: 필요한 table/stream read
- staging: own prefix write
- publish: catalog/table commit
- quality: read + metadata write
- consumer: published snapshot read

하나의 role이 source admin, object delete와 catalog update를 모두 갖지 않게 분리한다.

### row/column/domain control

분석용 aggregate와 raw PII 접근을 분리한다. policy가 query engine마다 다르면 우회 경로가 없는지 확인한다.

### temporary access

backfill과 incident 조사에 elevation이 필요하면 시간 제한, 승인, audit와 cleanup을 사용한다.

## secret과 log

- connection string/password를 DAG source와 notebook에 넣지 않는다.
- sample fixture는 실제 PII를 사용하지 않는다.
- error log에 raw payload 전체를 남기지 않는다.
- quarantine access를 production raw보다 느슨하게 두지 않는다.
- lineage facet에 민감 value가 아니라 schema/identifier만 남긴다.

## Secure quarantine와 repair evidence

Quarantine은 오류 record를 편리하게 모아 둔 공개 debug 공간이 아니다. 원본과 같은 classification을 상속하고 별도 workload identity, 최소 권한, 접근 audit와 짧은 retention을 적용한다.

Control metadata에는 raw payload 대신 가능한 범위에서 다음을 남긴다.

- stable record/event ID와 protected source location
- payload checksum, source snapshot/position과 observed time
- quality rule ID·version, rejection reason과 severity
- owner, disposition, exception expiry와 repair run ID
- 접근·승인·재처리·삭제 actor와 시각

원문 sample이 필요하면 redacted identifier와 제한된 secure sample store를 분리한다. 같은 ID의 conflicting payload는 어느 하나를 도착 순서로 승인하지 않고 conflict scope 전체를 보호된 quarantine에 유지한다.

Repair는 quarantine row를 직접 수정해 정상으로 바꾸지 않는다. Corrected source 또는 승인된 transform으로 새 run을 만들고 quality·reconciliation·lineage를 다시 생성한다. Repair 완료 뒤에도 원 rejection과 승인 근거는 audit retention 동안 남기고, raw·quarantine·derived·backup의 삭제 전파를 별도로 증명한다.

## encryption과 key boundary

- transport encryption
- storage encryption
- field/token encryption 필요 여부
- key rotation
- backup와 export의 별도 key/access

column-level encryption은 query, join, partition와 statistics에 영향을 준다. 보안 요구와 data processing trade-off를 함께 설계한다.

## retention

retention에는 여러 clock이 있다.

- event occurred time
- source commit time
- ingestion time
- dataset publish time
- legal hold 시작/종료

정책이 어느 시간을 기준으로 하는지 명시한다.

### layer별 retention

- source log
- raw capture
- canonical tables
- aggregates/features
- snapshots/time travel
- backups
- logs/traces
- quarantine
- local/temp files

raw를 지워도 derived table이 개인을 다시 식별할 수 있으면 삭제 요구가 완료되지 않을 수 있다.

## deletion propagation

삭제 요청 또는 정책 만료의 flow:

```text
request identity와 scope 확인
→ source/canonical key 매핑
→ affected datasets lineage 탐색
→ live tables delete/mask
→ snapshots와 files expiration 계획
→ downstream products 재계산/삭제
→ cache/index/export 처리
→ backup 정책 적용
→ evidence와 completion 기록
```

모든 backup에서 즉시 물리 삭제가 불가능할 수 있다. restore 시 삭제 ledger를 다시 적용하는 계약과 접근 제한을 둔다.

## legal hold

일반 retention 삭제보다 우선하는 보존 요구가 있을 수 있다.

- 대상 identity/기간/dataset
- 승인 authority
- expiration/review
- compaction·snapshot expiration 예외
- access logging
- hold 해제 후 deletion

hold를 이유로 모든 데이터를 무기한 보존하지 않는다.

## tenant isolation

multi-tenant data에서 확인한다.

- partition/path만으로 isolation을 주장하지 않음
- query predicate 누락 방지
- tenant-scoped identity와 access
- shared aggregate의 re-identification 위험
- backfill/export가 다른 tenant를 포함하지 않는지
- cache/temp/log isolation

## data sharing과 export

외부 전달은 새로운 data product와 owner를 만든다.

- schema와 purpose
- recipient identity
- minimum fields
- delivery encryption
- expiry/revocation
- downstream deletion 의무
- transfer log와 checksum

one-off CSV도 governance 밖이 아니다.

## audit와 evidence

- 누가 어떤 dataset/snapshot을 읽었는가
- 누가 schema/policy/retention을 변경했는가
- 어떤 pipeline run이 sensitive output을 만들었는가
- 삭제가 어느 dataset까지 완료됐는가
- break-glass access가 언제 종료됐는가

감사 log 자체의 민감성과 retention을 관리한다.

## 실패 모드

### raw forever

재현을 이유로 모든 payload를 무기한 저장한다. 목적과 최대 lookback에 맞춰 retention을 정한다.

### PII in partition path

object key와 metadata listing에 민감 값이 노출된다. pseudonymous/hashed partition과 access boundary를 사용한다.

### quarantine is public to engineers

잘못된 record payload가 더 넓은 권한에 노출된다. quarantine도 원본 classification을 유지한다.

### delete only current table

old snapshots, derived features, search index와 backup에 data가 남는다. lineage 기반 propagation과 restore-time deletion을 설계한다.

### shared superuser connector

모든 source와 sink에 광범위 권한을 가진 장기 credential이 있다. workload별 최소 권한과 rotation을 사용한다.

### logs leak payload

parse error에서 전체 record를 기록한다. redacted identifier, error code와 secure sample store를 분리한다.

## 검증 질문

1. 수집 목적과 필요한 최소 field를 설명할 수 있는가?
2. sensitive field가 raw·derived·log·backup 중 어디로 전파되는가?
3. workload identity별 source/read/write/commit 권한이 분리돼 있는가?
4. retention clock과 layer별 기간은 무엇인가?
5. deletion이 snapshot·derived·cache·backup까지 어떻게 전달되는가?
6. quarantine, debug와 export가 같은 classification을 유지하는가?
7. audit evidence가 실제 정책 변경과 접근을 추적하는가?

## 연결 연습

CDC capstone에서 data classification, field allowlist, retention과 deletion propagation artifact를 작성한다.

## 완료 기준

- data lifecycle 전체에 classification과 목적 제한을 적용한다.
- pipeline identity와 최소 권한을 data source/publish 경계로 분리한다.
- retention·delete·legal hold를 snapshot과 lineage 운영에 연결한다.
- 보안 주장을 access/audit/deletion evidence로 검증한다.
- quarantine의 classification·접근·repair·retention과 삭제 전파를 run-level evidence로 남긴다.
