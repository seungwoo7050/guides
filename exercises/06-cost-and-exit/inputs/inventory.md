# Resource와 workload 입력

- application VM 4개가 항상 실행됩니다. 평균 CPU 15%, zone failure 때 3개가 필요합니다.
- managed database는 minimum 2 capacity unit과 standby replica를 사용합니다.
- function은 하루 200,000회 실행되고 평균 2초, 실패 retry 8%입니다.
- object storage 10 TB, 월 5% 증가, versioning이 켜져 있습니다.
- 월 3 TB internet download, zone 간 transfer 1 TB입니다.
- log는 하루 300 GB ingest, 90일 hot retention입니다.
- unattached volume 12개, 오래된 snapshot 80개, owner 없는 test load balancer 7개가 있습니다.
- tenant usage는 document count만 기록하고 storage·egress는 tenant에 귀속하지 않습니다.
- database export throughput은 측정하지 않았습니다.
- 1년 commitment 제안을 검토 중입니다.
