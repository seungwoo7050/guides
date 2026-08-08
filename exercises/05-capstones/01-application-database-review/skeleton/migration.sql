-- TODO: 의미 보존 backfill과 호환 기간을 설계한다.
ALTER TABLE tickets ADD COLUMN priority integer NOT NULL DEFAULT 1;
ALTER TABLE tickets DROP COLUMN severity;
