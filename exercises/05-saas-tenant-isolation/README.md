# 05. SaaS tenant isolation

## 목적

request, database, object, cache, background job, analytics, support, export와 deletion의 모든 경로에 tenant context를 적용합니다.

## 입력

[`inputs/system-paths.md`](inputs/system-paths.md)를 사용합니다.

## 결과물

`tenant-isolation-review.md`를 완성합니다.

## 사람 검토 질문

1. tenant ID를 client input으로만 신뢰하지 않았습니까?
2. database query가 안전해도 cache·object·job이 leak하지 않습니까?
3. support access와 export가 audit됩니까?
4. plan entitlement와 tenant authorization을 혼동하지 않았습니까?
5. deletion이 derived data·queue·backup·key까지 전파됩니까?
