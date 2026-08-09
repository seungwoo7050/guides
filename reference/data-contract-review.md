# 데이터 계약 검토표

## 1. 소비자와 목적

- [ ] 소비자 또는 downstream job이 명확하다.
- [ ] 이 데이터가 어떤 결정을 가능하게 하는지 설명한다.
- [ ] source of truth와 파생 상태를 구분한다.
- [ ] data owner와 운영 연락 경로가 있다.

## 2. Grain과 identity

- [ ] record 하나의 grain을 문장으로 쓸 수 있다.
- [ ] stable key가 재실행·중복·수정에서도 유지된다.
- [ ] natural key와 surrogate key의 책임을 구분한다.
- [ ] key collision과 누락을 검사한다.

## 3. 시간

- [ ] event time, ingestion time, processing time을 구분한다.
- [ ] timezone과 calendar/day boundary를 명시한다.
- [ ] data interval의 경계가 `[start,end)`처럼 명확하다.
- [ ] late data와 correction window가 있다.

## 4. Schema

- [ ] field type뿐 아니라 단위·범위·enum 의미가 있다.
- [ ] required, nullable, default를 구분한다.
- [ ] backward/forward compatibility 방향을 정했다.
- [ ] rename, split, merge, semantic change 절차가 있다.
- [ ] producer와 consumer의 rollout 순서를 설명한다.

## 5. Change 의미

- [ ] insert/update/delete/correction을 구분한다.
- [ ] update가 full replacement인지 partial patch인지 명확하다.
- [ ] delete와 tombstone retention이 정의돼 있다.
- [ ] source position 또는 revision을 기록한다.

## 6. 품질과 freshness

- [ ] completeness, uniqueness, validity, consistency 검사가 있다.
- [ ] blocking check와 monitoring check를 구분한다.
- [ ] freshness 기준이 processing 완료가 아니라 consumer 반영 기준이다.
- [ ] 품질 실패 시 publish·격리·알림 절차가 있다.

## 7. 접근과 생명주기

- [ ] data classification이 있다.
- [ ] 최소 권한과 tenant 경계를 설명한다.
- [ ] retention·deletion·legal hold가 downstream에 전파된다.
- [ ] export와 공유 목적을 기록한다.

## 8. 버전과 lineage

- [ ] input snapshot/offset을 다시 찾을 수 있다.
- [ ] transform·schema·reference data version이 있다.
- [ ] output snapshot과 run ID가 연결된다.
- [ ] owner가 incident에서 전체 경로를 복원할 수 있다.
