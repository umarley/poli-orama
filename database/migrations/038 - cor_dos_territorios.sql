BEGIN;

ALTER TABLE territorio.territorio
    ADD COLUMN IF NOT EXISTS cor VARCHAR(7);

UPDATE territorio.territorio
SET cor = '#' || upper(substr(md5(id::text), 1, 6))
WHERE cor IS NULL;

ALTER TABLE territorio.territorio
    ALTER COLUMN cor SET DEFAULT '#1677FF',
    ALTER COLUMN cor SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_territorio_cor_hexadecimal'
          AND conrelid = 'territorio.territorio'::regclass
    ) THEN
        ALTER TABLE territorio.territorio
            ADD CONSTRAINT ck_territorio_cor_hexadecimal
            CHECK (cor ~ '^#[0-9A-Fa-f]{6}$');
    END IF;
END
$$;

COMMIT;
