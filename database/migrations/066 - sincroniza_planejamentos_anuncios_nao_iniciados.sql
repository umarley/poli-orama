BEGIN;

-- Planejamentos sem execucao continuam acompanhando o modelo da rota. O backfill
-- corrige snapshots criados antes dessa regra sem alterar o historico operacional.
CREATE TEMP TABLE tmp_planejamento_anuncio_sincronizavel
ON COMMIT DROP
AS
SELECT pl.id, pl.tenant_id, pl.rota_id
FROM anuncio.rota_comunicacao_planejamento pl
WHERE pl.status IN ('PLANEJADA', 'LIBERADA')
  AND NOT EXISTS (
      SELECT 1
      FROM anuncio.rota_comunicacao_execucao ex
      WHERE ex.tenant_id = pl.tenant_id
        AND ex.planejamento_id = pl.id
  );

UPDATE anuncio.rota_comunicacao_planejamento pl
SET rota_nome = r.nome,
    rota_descricao = r.descricao,
    territorio_id = r.territorio_id,
    territorio_nome = (
        SELECT t.nome
        FROM territorio.territorio t
        WHERE t.tenant_id = r.tenant_id
          AND t.id = r.territorio_id
    ),
    atualizado_em = now()
FROM tmp_planejamento_anuncio_sincronizavel sync
JOIN anuncio.rota_comunicacao r
  ON r.tenant_id = sync.tenant_id
 AND r.id = sync.rota_id
WHERE pl.tenant_id = sync.tenant_id
  AND pl.id = sync.id;

DELETE FROM anuncio.rota_comunicacao_planejamento_ponto pp
USING tmp_planejamento_anuncio_sincronizavel sync
WHERE pp.tenant_id = sync.tenant_id
  AND pp.planejamento_id = sync.id
  AND NOT EXISTS (
      SELECT 1
      FROM anuncio.rota_comunicacao_ponto rp
      WHERE rp.tenant_id = sync.tenant_id
        AND rp.rota_id = sync.rota_id
        AND rp.ordem = pp.ordem
  );

UPDATE anuncio.rota_comunicacao_planejamento_ponto pp
SET rota_ponto_origem_id = rp.id,
    descricao_local = rp.descricao_local,
    endereco = rp.endereco,
    latitude_planejada = rp.latitude_planejada,
    longitude_planejada = rp.longitude_planejada,
    observacao = rp.observacao,
    atualizado_em = now()
FROM tmp_planejamento_anuncio_sincronizavel sync
JOIN anuncio.rota_comunicacao_ponto rp
  ON rp.tenant_id = sync.tenant_id
 AND rp.rota_id = sync.rota_id
WHERE pp.tenant_id = sync.tenant_id
  AND pp.planejamento_id = sync.id
  AND pp.ordem = rp.ordem;

INSERT INTO anuncio.rota_comunicacao_planejamento_ponto (
    tenant_id,
    planejamento_id,
    rota_id,
    rota_ponto_origem_id,
    ordem,
    descricao_local,
    endereco,
    latitude_planejada,
    longitude_planejada,
    observacao
)
SELECT
    sync.tenant_id,
    sync.id,
    sync.rota_id,
    rp.id,
    rp.ordem,
    rp.descricao_local,
    rp.endereco,
    rp.latitude_planejada,
    rp.longitude_planejada,
    rp.observacao
FROM tmp_planejamento_anuncio_sincronizavel sync
JOIN anuncio.rota_comunicacao_ponto rp
  ON rp.tenant_id = sync.tenant_id
 AND rp.rota_id = sync.rota_id
WHERE NOT EXISTS (
    SELECT 1
    FROM anuncio.rota_comunicacao_planejamento_ponto pp
    WHERE pp.tenant_id = sync.tenant_id
      AND pp.planejamento_id = sync.id
      AND pp.ordem = rp.ordem
);

DELETE FROM anuncio.rota_comunicacao_planejamento_ponto_material pm
USING anuncio.rota_comunicacao_planejamento_ponto pp,
      tmp_planejamento_anuncio_sincronizavel sync
WHERE pm.tenant_id = pp.tenant_id
  AND pm.ponto_id = pp.id
  AND pp.tenant_id = sync.tenant_id
  AND pp.planejamento_id = sync.id;

INSERT INTO anuncio.rota_comunicacao_planejamento_ponto_material (
    tenant_id,
    ponto_id,
    material_id,
    quantidade_planejada
)
SELECT
    pp.tenant_id,
    pp.id,
    rpm.material_id,
    rpm.quantidade_planejada
FROM tmp_planejamento_anuncio_sincronizavel sync
JOIN anuncio.rota_comunicacao_planejamento_ponto pp
  ON pp.tenant_id = sync.tenant_id
 AND pp.planejamento_id = sync.id
JOIN anuncio.rota_comunicacao_ponto_material rpm
  ON rpm.tenant_id = pp.tenant_id
 AND rpm.ponto_id = pp.rota_ponto_origem_id;

COMMIT;
