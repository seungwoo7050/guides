# 시스템 경로

- 사용자는 JWT의 `user_id`와 request body의 `workspace_id`를 보냅니다.
- application은 `document_id`가 globally unique라며 일부 query에서 tenant filter를 생략합니다.
- cache key는 `document:{document_id}`입니다.
- object key는 `uploads/{workspace_id}/{document_id}`입니다.
- processing job에는 document ID만 들어 있습니다.
- support tool은 모든 tenant를 검색할 수 있지만 별도 reason이나 expiry가 없습니다.
- analytics export는 모든 tenant row를 한 file에 담고 dashboard에서 filter합니다.
- tenant export job은 database row와 object를 ZIP으로 묶습니다.
- tenant deletion은 primary database row만 지웁니다.
- starter plan은 월 100건, pro plan은 10,000건을 허용합니다.
