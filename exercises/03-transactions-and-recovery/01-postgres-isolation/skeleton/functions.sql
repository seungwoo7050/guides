CREATE OR REPLACE FUNCTION reserve_inventory(p_sku text, p_quantity integer)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE current_available integer;
BEGIN
    SELECT available INTO current_available
    FROM inventory
    WHERE sku = p_sku;

    PERFORM pg_sleep(1);
    IF current_available >= p_quantity THEN
        UPDATE inventory
        SET available = current_available - p_quantity
        WHERE sku = p_sku;
        RETURN true;
    END IF;
    RETURN false;
END $$;

CREATE OR REPLACE FUNCTION take_off_call(p_doctor_id integer)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE active_count integer;
BEGIN
    SELECT count(*) INTO active_count FROM doctors WHERE on_call;
    PERFORM pg_sleep(1);
    IF active_count <= 1 THEN
        RETURN false;
    END IF;
    UPDATE doctors SET on_call = false WHERE doctor_id = p_doctor_id;
    RETURN true;
END $$;
