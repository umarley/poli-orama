-- Calcula e atualiza cadastro.pessoa.completude_cadastral.
--
-- Tabelas consideradas no percentual:
-- - cadastro.pessoa: identificacao, qualificacao, foto e observacoes.
-- - cadastro.pessoa_documento: documentos civis/eleitorais.
-- - cadastro.pessoa_contato: telefone, celular, WhatsApp, e-mail e verificacao.
-- - cadastro.pessoa_endereco + cadastro.endereco: endereco vinculado e campos estruturados.
-- - cadastro.pessoa_pessoa_tipo: classificacao da pessoa.
-- - cadastro.eleitor: dados eleitorais.
-- - cadastro.lideranca + cadastro.hierarquia_lideranca: papel ou lideranca responsavel.
-- - territorio.pessoa_territorio: vinculos territoriais.
-- - cadastro.pessoa_tag, cadastro.pessoa_comunidade, cadastro.pessoa_nucleo_familiar:
--   segmentacao operacional.
-- - cadastro.pessoa_complemento_politico: perfil politico/complementar.
-- - cadastro.indicacao, cadastro.relacionamento_pessoa e cadastro.pessoa_rede_social:
--   contexto relacional e canais digitais.

CREATE OR REPLACE FUNCTION cadastro.calcular_completude_cadastral(p_pessoa_id BIGINT)
RETURNS NUMERIC(5,2)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_score NUMERIC(6,2) := 0;
BEGIN
    SELECT
        -- Dados minimos e qualificacao da pessoa: 20 pontos.
        (CASE WHEN NULLIF(BTRIM(p.nome_completo), '') IS NOT NULL THEN 8 ELSE 0 END) +
        (CASE WHEN p.data_nascimento IS NOT NULL THEN 3 ELSE 0 END) +
        (CASE WHEN p.sexo IS NOT NULL THEN 2 ELSE 0 END) +
        (CASE WHEN p.estado_civil IS NOT NULL THEN 2 ELSE 0 END) +
        (CASE WHEN p.escolaridade_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN p.profissao_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN p.religiao_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN p.foto_arquivo_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN NULLIF(BTRIM(p.observacoes), '') IS NOT NULL THEN 1 ELSE 0 END) +

        -- Documentos: 12 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_documento pd
             WHERE pd.tenant_id = p.tenant_id
               AND pd.pessoa_id = p.id
               AND pd.tipo_documento = 'cpf'
               AND NULLIF(BTRIM(pd.numero), '') IS NOT NULL
        ) THEN 6 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_documento pd
             WHERE pd.tenant_id = p.tenant_id
               AND pd.pessoa_id = p.id
               AND pd.tipo_documento IN ('rg', 'titulo_eleitor', 'cnh', 'passaporte', 'outro')
               AND NULLIF(BTRIM(pd.numero), '') IS NOT NULL
        ) THEN 4 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_documento pd
             WHERE pd.tenant_id = p.tenant_id
               AND pd.pessoa_id = p.id
               AND (NULLIF(BTRIM(pd.orgao_emissor), '') IS NOT NULL
                    OR pd.uf_emissor IS NOT NULL
                    OR pd.data_emissao IS NOT NULL)
        ) THEN 2 ELSE 0 END) +

        -- Contatos: 12 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_contato pc
             WHERE pc.tenant_id = p.tenant_id
               AND pc.pessoa_id = p.id
               AND pc.tipo_contato IN ('telefone', 'celular', 'whatsapp')
               AND NULLIF(BTRIM(pc.valor), '') IS NOT NULL
        ) THEN 5 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_contato pc
             WHERE pc.tenant_id = p.tenant_id
               AND pc.pessoa_id = p.id
               AND pc.tipo_contato = 'email'
               AND NULLIF(BTRIM(pc.valor), '') IS NOT NULL
        ) THEN 3 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_contato pc
             WHERE pc.tenant_id = p.tenant_id
               AND pc.pessoa_id = p.id
               AND pc.principal IS TRUE
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_contato pc
             WHERE pc.tenant_id = p.tenant_id
               AND pc.pessoa_id = p.id
               AND pc.verificado IS TRUE
        ) THEN 2 ELSE 0 END) +

        -- Endereco: 12 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_endereco pe
             WHERE pe.tenant_id = p.tenant_id
               AND pe.pessoa_id = p.id
        ) THEN 3 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_endereco pe
              JOIN cadastro.endereco e
                ON e.tenant_id = pe.tenant_id
               AND e.id = pe.endereco_id
             WHERE pe.tenant_id = p.tenant_id
               AND pe.pessoa_id = p.id
               AND e.codigo_municipio_ibge IS NOT NULL
        ) THEN 3 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_endereco pe
              JOIN cadastro.endereco e
                ON e.tenant_id = pe.tenant_id
               AND e.id = pe.endereco_id
             WHERE pe.tenant_id = p.tenant_id
               AND pe.pessoa_id = p.id
               AND (e.bairro_id IS NOT NULL OR NULLIF(BTRIM(e.bairro_texto), '') IS NOT NULL)
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_endereco pe
              JOIN cadastro.endereco e
                ON e.tenant_id = pe.tenant_id
               AND e.id = pe.endereco_id
             WHERE pe.tenant_id = p.tenant_id
               AND pe.pessoa_id = p.id
               AND NULLIF(BTRIM(e.logradouro), '') IS NOT NULL
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_endereco pe
              JOIN cadastro.endereco e
                ON e.tenant_id = pe.tenant_id
               AND e.id = pe.endereco_id
             WHERE pe.tenant_id = p.tenant_id
               AND pe.pessoa_id = p.id
               AND (NULLIF(BTRIM(e.cep), '') IS NOT NULL
                    OR e.latitude IS NOT NULL
                    OR e.longitude IS NOT NULL
                    OR e.geocodificado IS TRUE)
        ) THEN 2 ELSE 0 END) +

        -- Dados eleitorais: 10 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.eleitor el
             WHERE el.tenant_id = p.tenant_id
               AND el.pessoa_id = p.id
               AND NULLIF(BTRIM(el.titulo_eleitor), '') IS NOT NULL
        ) THEN 4 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.eleitor el
             WHERE el.tenant_id = p.tenant_id
               AND el.pessoa_id = p.id
               AND el.codigo_municipio_ibge IS NOT NULL
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.eleitor el
             WHERE el.tenant_id = p.tenant_id
               AND el.pessoa_id = p.id
               AND el.zona_eleitoral_id IS NOT NULL
        ) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.eleitor el
             WHERE el.tenant_id = p.tenant_id
               AND el.pessoa_id = p.id
               AND el.secao_eleitoral_id IS NOT NULL
        ) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.eleitor el
             WHERE el.tenant_id = p.tenant_id
               AND el.pessoa_id = p.id
               AND el.local_votacao_id IS NOT NULL
        ) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.eleitor el
             WHERE el.tenant_id = p.tenant_id
               AND el.pessoa_id = p.id
               AND el.situacao_titulo IS NOT NULL
        ) THEN 1 ELSE 0 END) +

        -- Classificacao e vinculos operacionais: 18 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_pessoa_tipo ppt
             WHERE ppt.tenant_id = p.tenant_id
               AND ppt.pessoa_id = p.id
        ) THEN 4 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.lideranca l
             WHERE l.tenant_id = p.tenant_id
               AND l.pessoa_id = p.id
               AND l.ativo IS TRUE
        ) OR EXISTS (
            SELECT 1
              FROM cadastro.hierarquia_lideranca hl
             WHERE hl.tenant_id = p.tenant_id
               AND hl.pessoa_subordinada_id = p.id
               AND hl.ativo IS TRUE
               AND (hl.data_fim IS NULL OR hl.data_fim >= CURRENT_DATE)
        ) THEN 5 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM territorio.pessoa_territorio pt
             WHERE pt.tenant_id = p.tenant_id
               AND pt.pessoa_id = p.id
        ) THEN 4 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_tag ptag
             WHERE ptag.tenant_id = p.tenant_id
               AND ptag.pessoa_id = p.id
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_comunidade pc
             WHERE pc.tenant_id = p.tenant_id
               AND pc.pessoa_id = p.id
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_nucleo_familiar pnf
             WHERE pnf.tenant_id = p.tenant_id
               AND pnf.pessoa_id = p.id
        ) THEN 1 ELSE 0 END) +

        -- Perfil politico/complementar: 8 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_complemento_politico pcp
             WHERE pcp.tenant_id = p.tenant_id
               AND pcp.pessoa_id = p.id
               AND NULLIF(BTRIM(pcp.vinculo_politico), '') IS NOT NULL
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_complemento_politico pcp
             WHERE pcp.tenant_id = p.tenant_id
               AND pcp.pessoa_id = p.id
               AND pcp.partido_id IS NOT NULL
        ) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_complemento_politico pcp
             WHERE pcp.tenant_id = p.tenant_id
               AND pcp.pessoa_id = p.id
               AND NULLIF(BTRIM(pcp.cargo_funcao), '') IS NOT NULL
        ) THEN 1 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_complemento_politico pcp
             WHERE pcp.tenant_id = p.tenant_id
               AND pcp.pessoa_id = p.id
               AND jsonb_array_length(COALESCE(pcp.temas_interesse, '[]'::jsonb)) > 0
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN p.nivel_engajamento IS NOT NULL OR EXISTS (
            SELECT 1
              FROM cadastro.pessoa_complemento_politico pcp
             WHERE pcp.tenant_id = p.tenant_id
               AND pcp.pessoa_id = p.id
               AND pcp.nivel_engajamento IS NOT NULL
        ) THEN 2 ELSE 0 END) +

        -- Contexto relacional e canais digitais: 8 pontos.
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.indicacao i
             WHERE i.tenant_id = p.tenant_id
               AND i.pessoa_indicada_id = p.id
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.relacionamento_pessoa rp
             WHERE rp.tenant_id = p.tenant_id
               AND (rp.pessoa_origem_id = p.id OR rp.pessoa_destino_id = p.id)
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN EXISTS (
            SELECT 1
              FROM cadastro.pessoa_rede_social prs
             WHERE prs.tenant_id = p.tenant_id
               AND prs.pessoa_id = p.id
               AND (NULLIF(BTRIM(prs.usuario_perfil), '') IS NOT NULL
                    OR NULLIF(BTRIM(prs.url), '') IS NOT NULL)
        ) THEN 2 ELSE 0 END) +
        (CASE WHEN p.fonte_dado_id IS NOT NULL THEN 1 ELSE 0 END) +
        (CASE WHEN p.score_confiabilidade IS NOT NULL THEN 1 ELSE 0 END)
    INTO v_score
    FROM cadastro.pessoa p
    WHERE p.id = p_pessoa_id;

    RETURN LEAST(100, GREATEST(0, COALESCE(v_score, 0)))::NUMERIC(5,2);
END;
$$;

COMMENT ON FUNCTION cadastro.calcular_completude_cadastral(BIGINT) IS
'Calcula o percentual de completude cadastral da pessoa a partir dos dados centrais, documentos, contatos, enderecos, eleitor, lideranca, territorio, segmentacoes e perfil complementar.';

CREATE OR REPLACE PROCEDURE cadastro.recalcular_completude_cadastral()
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE cadastro.pessoa p
       SET completude_cadastral = cadastro.calcular_completude_cadastral(p.id),
           atualizado_em = now()
     WHERE COALESCE(p.completude_cadastral, 0) < 100;
END;
$$;

COMMENT ON PROCEDURE cadastro.recalcular_completude_cadastral() IS
'Recalcula cadastro.pessoa.completude_cadastral para todas as pessoas com completude nula ou menor que 100. Execute com CALL cadastro.recalcular_completude_cadastral();';

CALL cadastro.recalcular_completude_cadastral();
