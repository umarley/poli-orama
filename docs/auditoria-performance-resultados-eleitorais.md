# Auditoria de performance dos resultados eleitorais

## Escopo e rastreamento

A busca de candidatos entra por `GET /api/v1/gestao-eleitoral/filtros/candidatos`,
passa por `GestaoEleitoralService.search_candidates` e termina em
`GestaoEleitoralRepository.search_candidates`. O frontend usa debounce de 300 ms,
habilita a consulta somente com eleição, cargo e ao menos dois caracteres e passa o
`AbortSignal` do TanStack Query ao cliente HTTP. O serviço mantém cache por tenant,
filtros, escopo territorial, termo normalizado e geração ativa do rollup.

O refresh é executado por `ElectionRollupProcessor.refresh`. O worker seleciona apenas
itens `pending`, toma um advisory lock transacional por eleição/turno e chama
`tse.fn_refresh_resultado_rollup`. A importação de resultados atualiza o catálogo de
votáveis e marca as chaves alteradas como `pending` na mesma transação da carga.

## Fatos comprovados no código

- A tabela bruta tem índices para eleição/turno, nome, cargo, município e seção. Não há
  evidência no repositório que justifique remover qualquer um deles.
- A busca textual usa `tse.resultado_votavel`, uma dimensão por eleição, turno, UF,
  cargo e número, com nome normalizado e índice GIN `gin_trgm_ops`; ela não agrupa mais
  a tabela bruta para o caso irrestrito.
- Escopos territoriais restritos ainda usam `EXISTS` na tabela bruta para comprovar que
  o candidato pertence ao território. O índice de nome por eleição reduz o conjunto,
  mas o custo real precisa ser confirmado no banco.
- A versão original do refresh fazia uma leitura/agregação independente da tabela
  bruta para a soma de origem, catálogo, localidades e quatro granularidades de voto.
- O ponteiro `active_generation` só é trocado após a validação dos totais; falhas
  revertem toda a transação.

## Alteração implementada

A migration 075 substitui a função de refresh sem alterar sua assinatura. Ela:

1. impede duas execuções simultâneas para a mesma eleição/turno, inclusive em chamadas
   diretas que contornem o worker;
2. lê `tse.resultados_eleicoes` uma vez para uma tabela temporária transacional;
3. cria o rollup de seção diretamente da granularidade única da fonte;
4. deriva local, zona e município, nessa ordem, sem reler a tabela de 16 GB;
5. reconstrói o catálogo de votáveis da chave usando a mesma fotografia;
6. compara o total de votos da fonte com todas as granularidades;
7. publica a nova geração atomicamente e só então remove a geração anterior.

A tabela temporária pode usar `temp_buffers` e arquivos temporários conforme o tamanho
da eleição. Isso troca várias leituras aleatórias/repetidas da tabela principal por uma
leitura e processamento sequencial intermediário; a melhoria efetiva deve ser medida no
ambiente representativo.

### Filtros de municípios e zonas

A migration 076 cria `tse.resultado_localidade_eleitoral`, com uma linha por eleição,
turno, UF, município e zona. O catálogo é preenchido a partir das gerações já ativas e
sincronizado, na mesma transação, sempre que o ponteiro do rollup muda.

As rotas `/filtros/municipios` e `/filtros/zonas` usam essa estrutura quando todas as
eleições selecionadas possuem geração pronta e o pedido não contém filtros que dependem
dos fatos de votação, como candidato, cargo, local ou seção. Consultas com esses filtros
continuam no caminho analítico anterior para preservar a semântica. Escopos por UF,
município e zona continuam sendo aplicados no catálogo; escopo por seção usa o fallback.

Isso remove do fluxo usual do frontend o agrupamento das tabelas por candidato/seção.
O catálogo tem cardinalidade proporcional à quantidade de zonas, não à quantidade de
votáveis multiplicada pelas seções.

## Hipóteses que exigem medição no banco

- Se o índice `(aa_eleicao, cd_eleicao, nr_turno)` tiver baixa correlação física, um
  bitmap heap scan ainda pode ler grande parte da tabela para eleições volumosas.
- Pesquisas com escopo municipal, zona ou seção podem gastar a maior parte do tempo nos
  `EXISTS` territoriais, não no GIN de nomes.
- `work_mem`, cache frio, concorrência e o armazenamento virtualizado podem mudar mais
  o tempo observado que o plano lógico isolado.
- A migration reduz leituras da tabela permanente, mas pode elevar temporariamente o
  I/O de `pgsql_tmp`. É necessário acompanhar ambos.

## Medições seguras

Execute primeiro em homologação ou réplica, com parâmetros reais. Para a busca:

```sql
EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS, VERBOSE, FORMAT TEXT)
SELECT base.nm_votavel,
       MIN(base.nr_votavel) AS nr_votavel,
       MIN(base.ds_cargo) AS ds_cargo
FROM tse.resultado_votavel base
WHERE base.aa_eleicao = 2024
  AND base.cd_eleicao = 619
  AND base.nr_turno = 1
  AND base.ds_cargo = ANY (ARRAY['PREFEITO']::text[])
  AND base.nm_votavel_busca ILIKE '%silva%'
GROUP BY base.nm_votavel
ORDER BY base.nm_votavel
LIMIT 40;
```

Repita com o `EXISTS` territorial produzido pelo backend para um usuário restrito.
Compare `actual rows`, linhas removidas por filtro, `shared hit/read`, blocos temporários,
sort em disco e divergência entre linhas estimadas e reais.

Não use `EXPLAIN ANALYZE` na função em produção: ela grava dados. Meça o refresh em
homologação, dentro de uma transação explicitamente revertida somente se houver espaço
para manter as duas gerações e a tabela temporária:

```sql
BEGIN;
SELECT clock_timestamp(), tse.fn_refresh_resultado_rollup(2024, 619, 1);
SELECT clock_timestamp();
ROLLBACK;
```

Durante a execução, registre `pg_stat_activity`, `pg_stat_io` (PostgreSQL 16+),
`pg_stat_statements`, `iostat` e o volume de arquivos temporários. Para verificar os
índices e o DDL reais antes da implantação:

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'tse'
  AND tablename IN ('resultados_eleicoes', 'resultado_votavel')
ORDER BY tablename, indexname;

SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('pg_trgm', 'unaccent');

SELECT version();
```

## Critérios de aceite

- Totais de votos idênticos entre fonte, seção, local, zona e município.
- Nenhuma geração parcial visível e apenas uma execução por chave.
- Busca retorna os mesmos nomes, números e cargos do catálogo anterior.
- Queda em tempo, `shared blocks read` e leituras da tabela permanente no refresh.
- Sem regressão relevante no tempo de importação ou no volume de arquivos temporários.

Não foram feitas medições antes/depois neste repositório porque ele não fornece acesso
ao banco de produção nem aos parâmetros reais observados. Os números devem ser anexados
ao relatório de implantação após o ensaio controlado.
