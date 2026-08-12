-- [Implementation 1] Correlated anti-join이 주문 존재 여부를 판정해 NULL 전파를 피한다.
CREATE VIEW q01_users_without_orders AS
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM orders AS o
    WHERE o.user_id = u.id
);

-- [Implementation 2] 차단 관계도 NOT EXISTS로 표현해 후보 집합의 NULL과 무관하게 사용자를 보존한다.
CREATE VIEW q02_unblocked_users AS
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM blocked_users AS b
    WHERE b.user_id = u.id
);

-- [Implementation 3] Users가 집계의 row owner이며 outer join의 빈 오른쪽을 0으로 정규화한다.
CREATE VIEW q03_user_totals AS
SELECT
    u.id,
    count(o.id)::integer AS order_count,
    coalesce(sum(o.total_cents), 0)::bigint AS total_cents
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id;

-- [Implementation 4] 합계 뒤 ID tie-break를 둔 순번이 LIMIT 결과의 안정성을 소유한다.
CREATE VIEW q04_ranked_spenders AS
SELECT id, order_count, total_cents, position
FROM (
    SELECT
        id,
        order_count,
        total_cents,
        row_number() OVER (ORDER BY total_cents DESC, id ASC)::integer AS position
    FROM q03_user_totals
) AS ranked
WHERE position <= 3;
