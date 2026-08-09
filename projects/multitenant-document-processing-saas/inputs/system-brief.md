# System brief

## 사용자와 tenant

- B2B 고객 organization이 tenant입니다.
- tenant admin은 member를 초대하고 role을 설정합니다.
- 한 사용자가 여러 tenant에 속할 수 있습니다.

## 기능

- PDF 또는 image upload
- metadata 저장
- async text extraction과 thumbnail 생성
- result download
- monthly processing quota
- usage dashboard
- tenant export
- tenant deletion

## Workload

- 평상시 초당 upload 2건, peak 50건
- 평균 object 8 MB, 최대 100 MB
- 처리 시간 평균 4초, p99 40초
- invalid file 1%, transient failure 2%
- 한 enterprise tenant가 전체 workload의 30%를 만들 수 있음

## 목표

- 다른 tenant data를 읽을 수 없어야 합니다.
- duplicate event는 output과 usage를 한 번만 만들어야 합니다.
- zone 하나의 compute 손실을 견뎌야 합니다.
- RPO 15분, RTO 60분을 목표로 합니다.
- starter 100건/월, pro 10,000건/월입니다.
- tenant export는 24시간 안에 준비합니다.
- deletion request는 active data를 7일 안에 제거하고 backup retention을 고지합니다.
- 월 cloud budget과 tenant별 unit cost를 추적합니다.

## 제약

- 작은 팀이 운영합니다.
- 실제 cloud provider는 아직 선택하지 않았습니다.
- GPU가 필요하지 않습니다.
- 모든 필수 검증은 로컬에서도 재현 가능해야 합니다.
