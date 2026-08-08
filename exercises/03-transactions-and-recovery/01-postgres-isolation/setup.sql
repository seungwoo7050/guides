CREATE TABLE inventory (
    sku text PRIMARY KEY,
    available integer NOT NULL CHECK (available >= 0)
);
INSERT INTO inventory(sku, available) VALUES ('book', 10);

CREATE TABLE shift_guard (
    id integer PRIMARY KEY CHECK (id = 1)
);
INSERT INTO shift_guard(id) VALUES (1);

CREATE TABLE doctors (
    doctor_id integer PRIMARY KEY,
    on_call boolean NOT NULL
);
INSERT INTO doctors(doctor_id, on_call) VALUES (1, true), (2, true);
