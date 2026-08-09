# 시스템 입력

- 공개 HTTPS API입니다.
- load balancer 뒤 application VM 2개가 있습니다.
- 두 VM은 현재 zone A에 있습니다.
- VM당 정상 처리량은 초당 100 request입니다.
- 평상시 120 request/s, peak는 180 request/s입니다.
- database는 private address의 단일 primary입니다.
- upload object는 object storage에 저장합니다.
- VM local disk에 thumbnail cache와 임시 변환 파일이 있습니다.
- image는 한 달 전에 수동으로 만들었습니다.
- startup script가 package repository에서 dependency를 설치합니다.
- automated snapshot은 켜져 있지만 restore 실험 기록은 없습니다.
- 모든 resource tag에는 environment만 있고 owner와 expires_at은 없습니다.
- load balancer, public address, unattached volume과 snapshot에도 별도 비용이 발생할 수 있습니다.
