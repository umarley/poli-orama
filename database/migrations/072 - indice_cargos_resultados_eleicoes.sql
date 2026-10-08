-- Permite listar os cargos distintos de uma eleicao sem percorrer todos
-- os votos por secao. CONCURRENTLY evita bloquear as cargas da tabela.
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_resultados_eleicoes_eleicao_cargo
    ON tse.resultados_eleicoes (aa_eleicao, cd_eleicao, nr_turno, ds_cargo);
