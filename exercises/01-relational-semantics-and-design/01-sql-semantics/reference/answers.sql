CREATE VIEW q01_users_without_orders AS
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM orders AS o
    WHERE o.user_id = u.id
);

CREATE VIEW q02_unblocked_users AS
SELECT u.id, u.email
FROM users AS u
WHERE NOT EXISTS (
    SELECT 1
    FROM blocked_users AS b
    WHERE b.user_id = u.id
);

CREATE VIEW q03_user_totals AS
SELECT
    u.id,
    count(o.id)::integer AS order_count,
    coalesce(sum(o.total_cents), 0)::bigint AS total_cents
FROM users AS u
LEFT JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id;

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
