# 단계 3: jthread와 협력적 취소

worker의 수명은 `JobRunner`가 소유합니다. 실행 중인 작업에는 `stop_token`을 전달하고, 대기 중인 작업은 queue에서 제거해 즉시 취소 상태로 전이합니다.

완료 조건은 다음과 같습니다.

- 소멸자가 join 가능한 thread를 남기지 않습니다.
- 취소는 강제 종료가 아니라 작업이 관찰하는 요청입니다.
- 첫 취소 요청만 true를 반환하고 반복 요청은 false로 수렴합니다.
- 정상 반환과 cancel이 경합해도 terminal commit에서 취소 요청을 다시 확인합니다.
- condition variable wait는 predicate와 stop token을 함께 사용합니다.
- Work가 token을 무시하면 `cancel()`은 요청만 발행하고 terminal 전이가 늦어지며, 외부 `stop()`과 destructor는 join을 기다린다는 한계를 설명합니다.
