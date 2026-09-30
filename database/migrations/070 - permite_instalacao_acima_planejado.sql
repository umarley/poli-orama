BEGIN;

-- A quantidade planejada e uma referencia operacional. A execucao deve registrar
-- a quantidade efetivamente instalada, inclusive quando ela superar o plano.
ALTER TABLE anuncio.rota_comunicacao_planejamento_ponto_material
    DROP CONSTRAINT IF EXISTS ck_planejamento_material_instalacao;

COMMIT;
