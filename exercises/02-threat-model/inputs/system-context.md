# BuildBoard 시스템 context

## 기능

개발자는 source archive와 build profile을 제출합니다. 시스템은 격리 runner에서 build를 실행하고 결과 artifact와 build log를 제공합니다.

## 흐름

```text
developer browser
  → gateway
  → build API
       ├→ job database
       └→ queue

queue
  → ephemeral runner
       ├→ package mirror
       ├→ source archive store
       └→ artifact store

CI control plane
  → runner image registry

모든 component
  → security event sink
```

## 알려진 상태

- gateway는 사용자 session을 검증하고 `user_id`를 내부 header로 전달합니다.
- build API는 job owner를 database에 저장합니다.
- runner는 job마다 생성된다고 설계돼 있으나 종료 실패율 자료는 없습니다.
- runner credential은 artifact store의 project prefix를 쓰는 권한이 있습니다.
- package mirror는 조직 내부 package와 공개 package cache를 함께 제공합니다.
- runner image는 tag로 배포 manifest에 기록돼 있습니다.
- artifact download URL은 10분 유효한 signed URL입니다.
- security event에는 `event_type`, `service`, `timestamp`가 있으나 actor·resource는 event별로 다릅니다.

## 범위

합성 staging 자료의 분석만 허용됩니다. 실제 package mirror, registry와 object store는 시험하지 않습니다.
