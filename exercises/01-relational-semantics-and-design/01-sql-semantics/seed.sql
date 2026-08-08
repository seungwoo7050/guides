INSERT INTO users(id, email) VALUES
    (1, 'a@example.test'),
    (2, 'b@example.test'),
    (3, 'c@example.test'),
    (4, 'd@example.test'),
    (5, 'e@example.test');

INSERT INTO orders(id, user_id, total_cents) VALUES
    (10, 1, 5000),
    (11, 1, 0),
    (12, 2, 0),
    (13, 4, 9000),
    (14, 4, 1000);

INSERT INTO blocked_users(user_id) VALUES (2), (NULL);
