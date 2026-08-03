BEGIN;

DO $script$
DECLARE
    v_tenant_id BIGINT;
    v_tipo_territorio_id SMALLINT;
    v_contextos_encontrados INTEGER;
    v_municipios_origem INTEGER;
    v_inseridos INTEGER;
    v_total_territorios INTEGER;
BEGIN
    -- Identifica univocamente o tenant e o tipo usados pelos quatro municipios
    -- que ja existem. Os codigos abaixo sao os codigos oficiais do IBGE.
    SELECT COUNT(*)
      INTO v_contextos_encontrados
      FROM (
          SELECT t.tenant_id, t.tipo_territorio_id
            FROM territorio.territorio AS t
            JOIN territorio.tipo_territorio AS tt
              ON tt.id = t.tipo_territorio_id
           WHERE tt.codigo = 'municipio'
             AND t.codigo_uf_ibge = 52
             AND t.codigo_municipio_ibge IN (
                 5208707, -- Goiania
                 5213806, -- Morrinhos
                 5219308, -- Santa Helena de Goias
                 5220454  -- Senador Canedo
             )
           GROUP BY t.tenant_id, t.tipo_territorio_id
          HAVING COUNT(DISTINCT t.codigo_municipio_ibge) = 4
      ) AS contexto;

    IF v_contextos_encontrados <> 1 THEN
        RAISE EXCEPTION
            'Esperado exatamente 1 tenant/tipo contendo os quatro municipios existentes; encontrados: %',
            v_contextos_encontrados;
    END IF;

    SELECT t.tenant_id, t.tipo_territorio_id
      INTO v_tenant_id, v_tipo_territorio_id
      FROM territorio.territorio AS t
      JOIN territorio.tipo_territorio AS tt
        ON tt.id = t.tipo_territorio_id
     WHERE tt.codigo = 'municipio'
       AND t.codigo_uf_ibge = 52
       AND t.codigo_municipio_ibge IN (5208707, 5213806, 5219308, 5220454)
     GROUP BY t.tenant_id, t.tipo_territorio_id
    HAVING COUNT(DISTINCT t.codigo_municipio_ibge) = 4;

    SELECT COUNT(*)
      INTO v_municipios_origem
      FROM global.municipio AS m
     WHERE m.codigo_uf_ibge = 52;

    IF v_municipios_origem <> 246 THEN
        RAISE EXCEPTION
            'A tabela global.municipio deveria conter 246 municipios de Goias, mas contem %',
            v_municipios_origem;
    END IF;

    INSERT INTO territorio.territorio (
        tenant_id,
        tipo_territorio_id,
        nome,
        codigo_uf_ibge,
        codigo_municipio_ibge,
        ativo
    )
    SELECT
        v_tenant_id,
        v_tipo_territorio_id,
        m.nome,
        m.codigo_uf_ibge,
        m.codigo_ibge,
        TRUE
      FROM global.municipio AS m
     WHERE m.codigo_uf_ibge = 52
       -- Os quatro registros informados ja existem e nao entram neste INSERT.
       AND m.codigo_ibge NOT IN (5208707, 5213806, 5219308, 5220454)
       -- Torna o script seguro para reexecucao e protege outros municipios
       -- que eventualmente ja tenham sido cadastrados.
       AND NOT EXISTS (
           SELECT 1
             FROM territorio.territorio AS existente
            WHERE existente.tenant_id = v_tenant_id
              AND existente.tipo_territorio_id = v_tipo_territorio_id
              AND existente.codigo_municipio_ibge = m.codigo_ibge
       )
     ORDER BY m.nome;

    GET DIAGNOSTICS v_inseridos = ROW_COUNT;

    SELECT COUNT(DISTINCT t.codigo_municipio_ibge)
      INTO v_total_territorios
      FROM territorio.territorio AS t
     WHERE t.tenant_id = v_tenant_id
       AND t.tipo_territorio_id = v_tipo_territorio_id
       AND t.codigo_uf_ibge = 52
       AND t.codigo_municipio_ibge IS NOT NULL;

    IF v_total_territorios <> 246 THEN
        RAISE EXCEPTION
            'Validacao final falhou: encontrados % territorios municipais de Goias; esperado: 246',
            v_total_territorios;
    END IF;

    RAISE NOTICE
        'Tenant %, tipo %, territorios inseridos nesta execucao: %, total de municipios de Goias: %',
        v_tenant_id,
        v_tipo_territorio_id,
        v_inseridos,
        v_total_territorios;
END;
$script$;

COMMIT;
