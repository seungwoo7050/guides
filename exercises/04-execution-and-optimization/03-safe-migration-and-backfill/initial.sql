CREATE TABLE orders (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    legacy_state text,
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO orders(legacy_state)
SELECT CASE g % 3 WHEN 0 THEN 'new' WHEN 1 THEN 'paid' ELSE 'cancelled' END
FROM generate_series(1, 5000) AS g;
