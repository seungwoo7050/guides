DO $$
DECLARE null_count bigint;
DECLARE mismatch_count bigint;
DECLARE is_required boolean;
BEGIN
    SELECT count(*) INTO null_count FROM orders WHERE status IS NULL;
    IF null_count <> 0 THEN
        RAISE EXCEPTION 'status backfill incomplete: % null rows', null_count;
    END IF;

    SELECT count(*) INTO mismatch_count
    FROM orders
    WHERE status <> upper(legacy_state);
    IF mismatch_count <> 0 THEN
        RAISE EXCEPTION 'status mapping mismatch: % rows', mismatch_count;
    END IF;

    SELECT (is_nullable = 'NO') INTO is_required
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='orders' AND column_name='status';
    IF is_required IS DISTINCT FROM true THEN
        RAISE EXCEPTION 'status is not NOT NULL';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname='public' AND indexname='orders_status_created_idx'
    ) THEN
        RAISE EXCEPTION 'status query index missing';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name='orders' AND column_name='legacy_state'
    ) THEN
        RAISE EXCEPTION 'legacy column was removed before compatibility window';
    END IF;

    BEGIN
        INSERT INTO orders(legacy_state, status) VALUES ('new', 'BROKEN');
        RAISE EXCEPTION 'invalid status was accepted';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    BEGIN
        INSERT INTO orders(legacy_state, status) VALUES ('new', NULL);
        RAISE EXCEPTION 'NULL status was accepted';
    EXCEPTION WHEN not_null_violation THEN NULL;
    END;
END $$;
