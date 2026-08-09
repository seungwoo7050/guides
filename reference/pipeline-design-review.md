# Pipeline 설계 검토표

## 입력 고정

- [ ] 처리할 source와 data interval을 고정한다.
- [ ] file manifest, table snapshot 또는 source offset을 기록한다.
- [ ] source mutation이 실행 중 결과를 바꾸지 않게 한다.
- [ ] reference data와 configuration version을 고정한다.

## 변환

- [ ] grain과 key 변화가 단계별로 명시돼 있다.
- [ ] filter·join·aggregation의 cardinality를 예측한다.
- [ ] duplicate와 correction을 처리하는 위치가 하나로 정해져 있다.
- [ ] nondeterministic 함수와 현재 시각 사용을 통제한다.
- [ ] skew, memory와 shuffle 비용을 관찰할 metric이 있다.

## 상태와 재시작

- [ ] source progress와 operator state를 함께 checkpoint한다.
- [ ] retry와 full replay를 구분한다.
- [ ] state schema change와 upgrade 절차가 있다.
- [ ] poison record와 malformed input의 격리 방식이 있다.

## Publish

- [ ] staging과 consumer-visible output을 분리한다.
- [ ] manifest/table snapshot/pointer commit 경계가 있다.
- [ ] 부분 output이 소비자에게 보이지 않는다.
- [ ] 같은 logical input의 재실행이 중복 snapshot 또는 row를 만들지 않는다.
- [ ] 이전 snapshot으로 rollback할 수 있다.

## Stream

- [ ] event time과 processing time을 구분한다.
- [ ] window, watermark, trigger, allowed lateness가 함께 정의돼 있다.
- [ ] sink result key와 correction/upsert version이 안정적이다.
- [ ] idle partition과 backpressure 정책이 있다.
- [ ] state TTL이 late/correction 계약보다 짧지 않다.

## CDC

- [ ] initial snapshot과 log position의 연결이 있다.
- [ ] transaction metadata와 source position을 보존한다.
- [ ] delete/tombstone과 stale resurrection을 다룬다.
- [ ] log retention 초과와 rebootstrap 절차가 있다.
- [ ] schema change와 connector restart를 시험한다.

## 검증과 운영

- [ ] 정상·경계·실패 fixture가 있다.
- [ ] count·key·aggregate reconciliation이 있다.
- [ ] freshness·quality·lineage가 같은 run/snapshot에 묶인다.
- [ ] canary·stop condition·resume·rollback이 있다.
- [ ] 실행 성공과 data correctness를 다른 신호로 관찰한다.
