BEGIN;

ALTER TABLE public.tenant_configuracao
    ALTER COLUMN preferencias
    SET DEFAULT '{"nomenclatura_liderancas":"liderancas"}'::jsonb;

UPDATE public.tenant_configuracao
SET preferencias = COALESCE(preferencias, '{}'::jsonb)
    || '{"nomenclatura_liderancas":"liderancas"}'::jsonb
WHERE NOT (COALESCE(preferencias, '{}'::jsonb) ? 'nomenclatura_liderancas');

COMMIT;
