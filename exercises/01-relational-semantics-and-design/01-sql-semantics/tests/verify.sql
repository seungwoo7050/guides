DO $$
DECLARE actual integer[];
BEGIN
    SELECT array_agg(id ORDER BY id) INTO actual FROM q01_users_without_orders;
    IF actual IS DISTINCT FROM ARRAY[3, 5] THEN
        RAISE EXCEPTION 'q01 mismatch: %', actual;
    END IF;
END $$;

DO $$
DECLARE actual integer[];
BEGIN
    SELECT array_agg(id ORDER BY id) INTO actual FROM q02_unblocked_users;
    IF actual IS DISTINCT FROM ARRAY[1, 3, 4, 5] THEN
        RAISE EXCEPTION 'q02 mismatch: %', actual;
    END IF;
END $$;

DO $$
DECLARE actual text;
BEGIN
    SELECT string_agg(format('%s:%s:%s', id, order_count, total_cents), ',' ORDER BY id)
    INTO actual
    FROM q03_user_totals;
    IF actual IS DISTINCT FROM '1:2:5000,2:1:0,3:0:0,4:2:10000,5:0:0' THEN
        RAISE EXCEPTION 'q03 mismatch: %', actual;
    END IF;
END $$;

DO $$
DECLARE actual text;
BEGIN
    SELECT string_agg(format('%s:%s', position, id), ',' ORDER BY position)
    INTO actual
    FROM q04_ranked_spenders;
    IF actual IS DISTINCT FROM '1:4,2:1,3:2' THEN
        RAISE EXCEPTION 'q04 ranking or tie order mismatch: %', actual;
    END IF;
END $$;
