-- TODO: 기존 행과 혼합 버전 배포를 고려한다.
ALTER TABLE orders
ADD COLUMN status text NOT NULL;

UPDATE orders SET status = upper(legacy_state);
