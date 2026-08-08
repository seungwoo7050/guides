-- TODO: 각 view의 의미 계약을 만족하도록 수정한다.
CREATE VIEW q01_users_without_orders AS
SELECT u.id, u.email
FROM users AS u
JOIN orders AS o ON o.user_id = u.id
WHERE o.id IS NULL;

CREATE VIEW q02_unblocked_users AS
SELECT u.id, u.email
FROM users AS u
WHERE u.id NOT IN (SELECT user_id FROM blocked_users);

CREATE VIEW q03_user_totals AS
SELECT u.id, count(*) AS order_count, sum(o.total_cents) AS total_cents
FROM users AS u
JOIN orders AS o ON o.user_id = u.id
GROUP BY u.id;

CREATE VIEW q04_ranked_spenders AS
SELECT *
FROM q03_user_totals
ORDER BY total_cents DESC
LIMIT 3;
