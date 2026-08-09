# NoteRelay 시스템 요약

## 사용자 기능

사용자는 HTTPS API에서 텍스트 또는 PDF 문서를 업로드하고, 변환이 끝나면 미리보기 URL을 받습니다. 업로드와 미리보기 metadata는 `document-api`가 관리합니다.

## 구성요소

```text
browser
  → public gateway
  → document-api
       ├→ metadata database
       ├→ conversion queue
       └→ object storage provider

conversion queue
  → preview-worker
       ├→ object storage provider
       └→ internal package mirror

모든 서비스
  → audit sink
```

## Identity

- gateway는 `document-api`에 고정 service token으로 요청합니다.
- `document-api`와 `preview-worker`는 서로 다른 workload identity를 사용한다고 설계 문서에 적혀 있습니다.
- object storage provider의 bucket policy 전문은 제공되지 않았습니다.
- 로컬 개발 환경에서는 두 서비스가 하나의 `.env` 파일을 공유합니다.

## 환경

- 합성 staging environment만 평가 허가가 검토 중입니다.
- production과 staging은 같은 외부 object storage provider 계정에 속하지만 bucket은 다르다고 운영자가 설명했습니다.
- worker subnet은 문서상 private로 표시돼 있습니다.
- egress gateway의 runtime rule export는 아직 제공되지 않았습니다.

## 현재 증거

- architecture diagram: 45일 전 갱신
- repository configuration snapshot: 3일 전 생성
- staging deployment manifest: 12일 전 생성
- 운영자 인터뷰 메모: 오늘 작성
- runtime network flow log: 미제공
- object access audit: actor field가 없는 일부 샘플만 제공
