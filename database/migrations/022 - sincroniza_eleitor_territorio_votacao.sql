BEGIN;

-- Um tenant deve possuir no maximo um territorio do mesmo tipo para cada bairro.
-- Alem de evitar duplicidade funcional, este indice torna a criacao feita pela
-- trigger segura quando varios eleitores do mesmo bairro sao atualizados ao mesmo tempo.
CREATE UNIQUE INDEX IF NOT EXISTS uq_territorio_bairro_tipo_tenant
    ON territorio.territorio (tenant_id, tipo_territorio_id, bairro_id)
    WHERE bairro_id IS NOT NULL;

CREATE OR REPLACE FUNCTION territorio.fn_sincroniza_eleitor_territorio_votacao()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_bairro_id INTEGER;
    v_bairro_nome VARCHAR(150);
    v_codigo_municipio_ibge INTEGER;
    v_codigo_uf_ibge SMALLINT;
    v_latitude NUMERIC(10, 7);
    v_longitude NUMERIC(10, 7);
    v_territorio_id BIGINT;
    v_vinculo_id BIGINT;
BEGIN
    -- Se o local foi removido, o vinculo de votacao anterior deixa de ser valido.
    IF NEW.local_votacao_id IS NULL THEN
        DELETE FROM territorio.pessoa_territorio
         WHERE tenant_id = NEW.tenant_id
           AND pessoa_id = NEW.pessoa_id
           AND vinculo = 'votacao';
        RETURN NEW;
    END IF;

    SELECT lv.bairro_id,
           b.nome,
           lv.codigo_municipio_ibge,
           m.codigo_uf_ibge,
           lv.latitude,
           lv.longitude
      INTO v_bairro_id,
           v_bairro_nome,
           v_codigo_municipio_ibge,
           v_codigo_uf_ibge,
           v_latitude,
           v_longitude
      FROM global.local_votacao lv
      LEFT JOIN global.bairro b
        ON b.id = lv.bairro_id
      LEFT JOIN global.municipio m
        ON m.codigo_ibge = lv.codigo_municipio_ibge
     WHERE lv.id = NEW.local_votacao_id;

    -- Sem bairro nao e possivel determinar o territorio de votacao. As coordenadas
    -- permanecem no local de votacao, pois territorio.geom armazena MultiPolygon.
    IF NOT FOUND OR v_bairro_id IS NULL OR v_bairro_nome IS NULL THEN
        DELETE FROM territorio.pessoa_territorio
         WHERE tenant_id = NEW.tenant_id
           AND pessoa_id = NEW.pessoa_id
           AND vinculo = 'votacao';
        RETURN NEW;
    END IF;

    -- Latitude e longitude sao obtidas junto com o local. Elas nao sao copiadas para
    -- territorio.territorio porque esse campo geografico representa o poligono do bairro.
    -- O vinculo territorial e determinado pela chave oficial global.bairro.id.
    PERFORM v_latitude, v_longitude;

    INSERT INTO territorio.territorio (
        tenant_id,
        tipo_territorio_id,
        nome,
        codigo_uf_ibge,
        codigo_municipio_ibge,
        bairro_id,
        ativo
    )
    VALUES (
        NEW.tenant_id,
        3,
        v_bairro_nome,
        v_codigo_uf_ibge,
        v_codigo_municipio_ibge,
        v_bairro_id,
        TRUE
    )
    ON CONFLICT (tenant_id, tipo_territorio_id, bairro_id)
        WHERE bairro_id IS NOT NULL
    DO NOTHING
    RETURNING id INTO v_territorio_id;

    IF v_territorio_id IS NULL THEN
        SELECT t.id
          INTO v_territorio_id
          FROM territorio.territorio t
         WHERE t.tenant_id = NEW.tenant_id
           AND t.tipo_territorio_id = 3
           AND t.bairro_id = v_bairro_id;
    END IF;

    -- Reutiliza primeiro um eventual vinculo que ja aponte para o territorio correto.
    SELECT pt.id
      INTO v_vinculo_id
      FROM territorio.pessoa_territorio pt
     WHERE pt.tenant_id = NEW.tenant_id
       AND pt.pessoa_id = NEW.pessoa_id
       AND pt.territorio_id = v_territorio_id
       AND pt.vinculo = 'votacao'
     ORDER BY pt.id
     LIMIT 1;

    IF v_vinculo_id IS NULL THEN
        -- Se o local mudou, aproveita o vinculo de votacao anterior em vez de criar
        -- historicos conflitantes para a mesma pessoa.
        SELECT pt.id
          INTO v_vinculo_id
          FROM territorio.pessoa_territorio pt
         WHERE pt.tenant_id = NEW.tenant_id
           AND pt.pessoa_id = NEW.pessoa_id
           AND pt.vinculo = 'votacao'
         ORDER BY pt.id
         LIMIT 1;

        IF v_vinculo_id IS NULL THEN
            INSERT INTO territorio.pessoa_territorio (
                tenant_id,
                pessoa_id,
                territorio_id,
                vinculo
            )
            VALUES (
                NEW.tenant_id,
                NEW.pessoa_id,
                v_territorio_id,
                'votacao'
            )
            RETURNING id INTO v_vinculo_id;
        ELSE
            UPDATE territorio.pessoa_territorio
               SET territorio_id = v_territorio_id
             WHERE id = v_vinculo_id;
        END IF;
    END IF;

    -- Mantem apenas o vinculo de votacao correspondente ao local atual.
    DELETE FROM territorio.pessoa_territorio
     WHERE tenant_id = NEW.tenant_id
       AND pessoa_id = NEW.pessoa_id
       AND vinculo = 'votacao'
       AND id <> v_vinculo_id;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sincroniza_eleitor_territorio_votacao
    ON cadastro.eleitor;

CREATE TRIGGER trg_sincroniza_eleitor_territorio_votacao
AFTER INSERT OR UPDATE OF local_votacao_id
ON cadastro.eleitor
FOR EACH ROW
EXECUTE FUNCTION territorio.fn_sincroniza_eleitor_territorio_votacao();

COMMIT;
