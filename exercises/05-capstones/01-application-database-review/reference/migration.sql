ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority integer;

UPDATE tickets
SET priority = CASE severity
    WHEN 'CRITICAL' THEN 5
    WHEN 'HIGH' THEN 4
    WHEN 'MEDIUM' THEN 3
    WHEN 'LOW' THEN 2
END
WHERE priority IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'tickets'::regclass
          AND conname = 'tickets_priority_range'
    ) THEN
        EXECUTE 'ALTER TABLE tickets ADD CONSTRAINT tickets_priority_range CHECK (priority BETWEEN 1 AND 5) NOT VALID';
    END IF;
END $$;

ALTER TABLE tickets VALIDATE CONSTRAINT tickets_priority_range;
ALTER TABLE tickets ALTER COLUMN priority SET NOT NULL;
-- severity는 구버전 reader와 rollback 가능성을 위해 compatibility window 동안 유지한다.
