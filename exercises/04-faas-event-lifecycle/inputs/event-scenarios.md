# Event 시나리오

문서가 object storage에 업로드되면 queue가 function을 호출합니다. function은 원본을 읽고 변환 결과를 object storage에 저장하며 database status와 tenant usage를 갱신합니다.

실패 사례:

1. 결과 object 저장 뒤 database update 전에 timeout
2. 같은 provider event가 두 번 전달
3. 변환할 수 없는 파일이 모든 retry에서 실패
4. 10개 batch 중 하나가 실패
5. 한 tenant가 10,000개 event를 생성해 공유 concurrency를 독점
6. tenant가 삭제된 뒤 늦은 retry 도착
7. 새 function version이 event schema v1을 더 이상 이해하지 못함
8. dead-letter event를 운영자가 수동 replay
