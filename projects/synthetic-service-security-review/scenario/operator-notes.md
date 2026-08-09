# 운영자 Notes

> 이 메모는 incident 채널에서 수집한 문장으로, 확인된 사실과 추측이 섞여 있습니다.

- 10:23 — “tenant-42 read는 job-81과 관계없는 것 같습니다.”
- 10:24 — “새 worker image가 방금 배포됐으니 image 문제일 수 있습니다.”
- 10:27 — “package proxy가 왜 public-cache를 선택했는지는 lockfile을 확인해야 합니다.”
- 10:29 — “stable tag는 CI identity만 바꾸지만 사람이 release approval을 했습니다.”
- 10:30 — “worker를 지우면 memory와 local log를 잃을 수 있습니다.”
- 10:32 — “cred-201은 이미 expiry를 지났다고 생각했는데 object proxy는 허용했습니다.”
- 10:34 — “동일 credential의 다른 object read가 더 있는지는 sink 지연 때문에 아직 모릅니다.”
- 10:38 — “이전 digest rollback 뒤 service가 ready입니다.”
- 10:40 — “synthetic report smoke는 성공했습니다.”
- 10:43 — “이전 digest가 trusted하다는 근거는 지난 release 기록뿐입니다.”
- 10:46 — “runtime digest를 node에서 수집하는 event가 없습니다.”
- 10:50 — “object provider audit 전문은 별도 팀 승인이 필요합니다.”
