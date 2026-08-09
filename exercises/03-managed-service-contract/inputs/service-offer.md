# 가상 관리형 서비스 제안

## Database

- engine patch와 host replacement를 공급자가 수행합니다.
- 두 zone replica 옵션이 있습니다.
- automated backup과 14일 point-in-time recovery를 제공합니다.
- major version은 일정 뒤 지원 종료됩니다.
- connection 500개, storage 2 TB limit가 있습니다.
- extension 일부는 사용할 수 없습니다.

## Queue

- message를 durable하게 저장한다고 설명합니다.
- consumer가 실패하면 재전달할 수 있습니다.
- ordering은 partition key 내부에서만 제공됩니다.
- retention 7일, payload 1 MB, throughput quota가 있습니다.

## Object service

- versioning과 lifecycle을 제공합니다.
- private endpoint와 public endpoint를 선택할 수 있습니다.
- request·storage·retrieval·egress에 비용이 연결됩니다.
- 대량 export throughput과 deletion completion time은 제안서에 없습니다.
