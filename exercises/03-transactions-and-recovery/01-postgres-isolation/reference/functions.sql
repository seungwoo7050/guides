CREATE OR REPLACE FUNCTION reserve_inventory(p_sku text, p_quantity integer)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE changed integer;
BEGIN
    IF p_quantity <= 0 THEN
        RAISE EXCEPTION 'quantity must be positive';
    END IF;

    UPDATE inventory
    SET available = available - p_quantity
    WHERE sku = p_sku
      AND available >= p_quantity;
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END $$;

CREATE OR REPLACE FUNCTION take_off_call(p_doctor_id integer)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE active_count integer;
DECLARE changed integer;
BEGIN
    -- 업무 불변식을 공유하는 모든 transaction이 같은 guard row를 잠근다.
    PERFORM id FROM shift_guard WHERE id = 1 FOR UPDATE;
    SELECT count(*) INTO active_count FROM doctors WHERE on_call;
    IF active_count <= 1 THEN
        RETURN false;
    END IF;
    UPDATE doctors
    SET on_call = false
    WHERE doctor_id = p_doctor_id AND on_call;
    GET DIAGNOSTICS changed = ROW_COUNT;
    RETURN changed = 1;
END $$;
