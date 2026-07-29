BEGIN;

-- Garante uma unica representacao territorial de cada bairro por tenant.
CREATE UNIQUE INDEX IF NOT EXISTS uq_territorio_bairro_tipo_tenant
    ON territorio.territorio (tenant_id, tipo_territorio_id, bairro_id)
    WHERE bairro_id IS NOT NULL;

CREATE OR REPLACE FUNCTION territorio.fn_sincroniza_pessoa_territorio_moradia(
    p_tenant_id BIGINT,
    p_pessoa_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_bairro_id INTEGER;
    v_bairro_nome VARCHAR(150);
    v_codigo_municipio_ibge INTEGER;
    v_codigo_uf_ibge SMALLINT;
    v_territorio_id BIGINT;
    v_vinculo_id BIGINT;
BEGIN
    -- Usa o endereco residencial principal. Na ausencia dele, utiliza o primeiro
    -- endereco residencial associado a pessoa.
    SELECT COALESCE(
               e.bairro_id,
               (
                   SELECT b_resolvido.id
                     FROM global.bairro b_resolvido
                    WHERE b_resolvido.codigo_municipio_ibge = e.codigo_municipio_ibge
                      AND unaccent(lower(btrim(b_resolvido.nome))) =
                          unaccent(lower(btrim(e.bairro_texto)))
                    ORDER BY
                        CASE WHEN b_resolvido.origem = 'oficial' THEN 0 ELSE 1 END,
                        b_resolvido.id
                    LIMIT 1
               )
           ),
           e.codigo_municipio_ibge
      INTO v_bairro_id,
           v_codigo_municipio_ibge
      FROM cadastro.pessoa_endereco pe
      JOIN cadastro.endereco e
        ON e.id = pe.endereco_id
       AND e.tenant_id = pe.tenant_id
     WHERE pe.tenant_id = p_tenant_id
       AND pe.pessoa_id = p_pessoa_id
       AND pe.tipo = 'residencial'
     ORDER BY pe.principal DESC, pe.id
     LIMIT 1;

    -- Sem endereco residencial ou bairro reconhecido, nao existe territorio de
    -- moradia que possa ser mantido automaticamente.
    IF NOT FOUND OR v_bairro_id IS NULL THEN
        DELETE FROM territorio.pessoa_territorio
         WHERE tenant_id = p_tenant_id
           AND pessoa_id = p_pessoa_id
           AND vinculo = 'moradia';
        RETURN;
    END IF;

    SELECT b.nome,
           b.codigo_municipio_ibge,
           m.codigo_uf_ibge
      INTO v_bairro_nome,
           v_codigo_municipio_ibge,
           v_codigo_uf_ibge
      FROM global.bairro b
      JOIN global.municipio m
        ON m.codigo_ibge = b.codigo_municipio_ibge
     WHERE b.id = v_bairro_id;

    IF NOT FOUND THEN
        DELETE FROM territorio.pessoa_territorio
         WHERE tenant_id = p_tenant_id
           AND pessoa_id = p_pessoa_id
           AND vinculo = 'moradia';
        RETURN;
    END IF;

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
        p_tenant_id,
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
         WHERE t.tenant_id = p_tenant_id
           AND t.tipo_territorio_id = 3
           AND t.bairro_id = v_bairro_id;
    END IF;

    -- Preserva o vinculo caso ele ja esteja correto.
    SELECT pt.id
      INTO v_vinculo_id
      FROM territorio.pessoa_territorio pt
     WHERE pt.tenant_id = p_tenant_id
       AND pt.pessoa_id = p_pessoa_id
       AND pt.territorio_id = v_territorio_id
       AND pt.vinculo = 'moradia'
     ORDER BY pt.id
     LIMIT 1;

    IF v_vinculo_id IS NULL THEN
        -- Quando a pessoa muda de bairro, atualiza o vinculo anterior.
        SELECT pt.id
          INTO v_vinculo_id
          FROM territorio.pessoa_territorio pt
         WHERE pt.tenant_id = p_tenant_id
           AND pt.pessoa_id = p_pessoa_id
           AND pt.vinculo = 'moradia'
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
                p_tenant_id,
                p_pessoa_id,
                v_territorio_id,
                'moradia'
            )
            RETURNING id INTO v_vinculo_id;
        ELSE
            UPDATE territorio.pessoa_territorio
               SET territorio_id = v_territorio_id
             WHERE id = v_vinculo_id;
        END IF;
    END IF;

    -- Uma pessoa possui somente um territorio de moradia automatico vigente.
    DELETE FROM territorio.pessoa_territorio
     WHERE tenant_id = p_tenant_id
       AND pessoa_id = p_pessoa_id
       AND vinculo = 'moradia'
       AND id <> v_vinculo_id;
END;
$$;

CREATE OR REPLACE FUNCTION territorio.fn_endereco_dispara_sincronizacao_moradia()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_pessoa RECORD;
BEGIN
    FOR v_pessoa IN
        SELECT pe.tenant_id,
               pe.pessoa_id
          FROM cadastro.pessoa_endereco pe
         WHERE pe.endereco_id = NEW.id
           AND pe.tenant_id = NEW.tenant_id
    LOOP
        PERFORM territorio.fn_sincroniza_pessoa_territorio_moradia(
            v_pessoa.tenant_id,
            v_pessoa.pessoa_id
        );
    END LOOP;

    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION territorio.fn_pessoa_endereco_dispara_sincronizacao_moradia()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        PERFORM territorio.fn_sincroniza_pessoa_territorio_moradia(
            OLD.tenant_id,
            OLD.pessoa_id
        );
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        PERFORM territorio.fn_sincroniza_pessoa_territorio_moradia(
            NEW.tenant_id,
            NEW.pessoa_id
        );
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sincroniza_endereco_territorio_moradia
    ON cadastro.endereco;

CREATE TRIGGER trg_sincroniza_endereco_territorio_moradia
AFTER INSERT OR UPDATE
ON cadastro.endereco
FOR EACH ROW
EXECUTE FUNCTION territorio.fn_endereco_dispara_sincronizacao_moradia();

-- O INSERT do endereco ocorre antes da associacao em cadastro.pessoa_endereco.
-- Este segundo gatilho garante a sincronizacao assim que a pessoa for vinculada.
DROP TRIGGER IF EXISTS trg_sincroniza_pessoa_endereco_territorio_moradia
    ON cadastro.pessoa_endereco;

CREATE TRIGGER trg_sincroniza_pessoa_endereco_territorio_moradia
AFTER INSERT OR UPDATE OR DELETE
ON cadastro.pessoa_endereco
FOR EACH ROW
EXECUTE FUNCTION territorio.fn_pessoa_endereco_dispara_sincronizacao_moradia();

COMMIT;
