# SPEC-15 - NLP, ML e Inteligencia Avancada

Prioridade principal: P3  
Modulo: `backend_jobs_celery`, `etl`, `dw`, `mod_dashboard`  
Objetivo: adicionar processamento inteligente para classificar demandas e pautas, prever riscos, identificar apoiadores ativos e sugerir acoes territoriais.

## Escopo futuro

- Classificacao automatica de demandas.
- Extracao de entidades de textos, convites e pautas.
- Identificacao de recorrencia de problemas.
- Score de engajamento.
- Risco de meta nao atingida.
- Sugestoes de territorios prioritarios.

## Fora do MVP

- Decisao automatica sem revisao humana.
- Modelos sem explicabilidade minima.
- Uso de dados sensiveis sem avaliacao LGPD.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| IA-001 | P3 | Produto/Dados | Definir casos de uso prioritarios de IA. | Documento aprova classificacao de demandas, risco de meta e engajamento. |
| IA-002 | P3 | Dados | Criar dicionario de categorias e taxonomia. | Categorias de demanda, pauta e territorio estao normalizadas. |
| IA-003 | P3 | Dados | Definir dataset de treino/validacao. | Amostra anonimizavel e representativa fica documentada. |
| IA-004 | P3 | Juridico | Avaliar base legal para uso de dados sensiveis. | Checklist LGPD aprovado antes de treino/uso. |
| IA-005 | P3 | Jobs | Criar pipeline de preprocessamento de texto. | Texto e limpo, normalizado e tokenizado. |
| IA-006 | P3 | Jobs | Criar classificador inicial de demandas por regra/keyword. | Sistema sugere categoria com confianca basica. |
| IA-007 | P3 | Jobs | Criar classificador ML de demandas. | Modelo supera baseline definido em dataset validado. |
| IA-008 | P3 | Backend | Criar endpoint de sugestao de categoria. | Ao digitar demanda, API retorna sugestao e confianca. |
| IA-009 | P3 | Frontend | Exibir sugestao de categoria no formulario de demanda. | Usuario aceita, troca ou ignora sugestao. |
| IA-010 | P3 | Jobs | Criar extracao de entidades de pautas/convites. | Sistema identifica temas, localidades, pessoas e organizacoes quando possivel. |
| IA-011 | P3 | Jobs | Criar agregacao de recorrencia de problemas. | Dashboard mostra temas recorrentes por territorio. |
| IA-012 | P3 | Dados | Definir formula de score de engajamento. | Score considera eventos, demandas, interacoes e cadastros com pesos documentados. |
| IA-013 | P3 | Jobs | Criar job de score de engajamento. | Pessoas/lideres recebem score recalculado periodicamente. |
| IA-014 | P3 | Backend | Criar endpoint de ranking de apoiadores ativos. | Ranking retorna criterios e filtros. |
| IA-015 | P3 | Frontend | Criar painel de engajamento. | Gestor ve apoiadores/lideres ativos e tendencia. |
| IA-016 | P3 | Dados | Definir features de risco de meta. | Features usam cadastros, historico, territorio, eventos, demandas e engajamento. |
| IA-017 | P3 | Jobs | Criar modelo inicial de risco de meta. | Modelo retorna risco baixo/medio/alto com explicacao simples. |
| IA-018 | P3 | Backend | Criar endpoint de risco de meta. | Meta exibe risco e principais fatores. |
| IA-019 | P3 | Frontend | Exibir risco no detalhe de meta. | Usuario ve fatores acionaveis. |
| IA-020 | P3 | Dados | Criar metodologia de sugestao territorial. | Regras/modelo apontam bairros/zonas com oportunidade ou risco. |
| IA-021 | P3 | Backend | Criar endpoint de territorios prioritarios. | Retorna territorio, motivo, indicador e sugestao. |
| IA-022 | P3 | Frontend | Criar painel de recomendacoes. | Gestor visualiza acoes sugeridas por territorio. |
| IA-023 | P3 | MLOps | Versionar modelos e datasets. | Cada predicao pode ser rastreada para versao do modelo. |
| IA-024 | P3 | MLOps | Criar monitoramento de drift e qualidade. | Alertas aparecem quando dados mudam ou desempenho cai. |
| IA-025 | P3 | QA | Validar vies e dados sensiveis. | Revisao documenta riscos e mitigacoes. |

## Regras de negocio

- Sugestoes de IA devem ser assistivas, nao decisorias.
- Usuario deve poder corrigir categoria sugerida.
- Modelos devem registrar versao e confianca.
- Dados sensiveis exigem minimizacao, permissao e auditoria.
- Explicacoes simples sao obrigatorias para risco e recomendacoes.

## Entidades relacionadas

- `demanda.demanda`
- `agenda.pauta_evento`
- `arquivo.documento_extraido`
- `meta.meta_voto`
- `meta.acompanhamento_meta`
- `dw.fato_demanda`
- `dw.fato_evento`
- `dw.fato_meta_voto`
- `dw.fato_interacao`
- `etl.job_processamento`
- `etl.log_processamento`

## Definition of Done

- Casos de uso e base legal estao aprovados.
- Sugestoes sao auditaveis, explicaveis e revisaveis por usuario.
- Modelos possuem baseline, metricas e versao.
- UI apresenta IA como apoio a decisao.
