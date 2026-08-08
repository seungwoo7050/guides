CREATE TABLE users (
    id integer PRIMARY KEY,
    email text NOT NULL UNIQUE
);

CREATE TABLE orders (
    id integer PRIMARY KEY,
    user_id integer NOT NULL REFERENCES users(id),
    total_cents integer NOT NULL CHECK (total_cents >= 0)
);

-- NULL이 섞인 NOT IN의 위험을 관찰하기 위해 의도적으로 nullable이다.
CREATE TABLE blocked_users (
    user_id integer REFERENCES users(id)
);
