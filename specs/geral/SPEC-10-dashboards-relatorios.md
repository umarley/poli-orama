# SPEC-10 - Dashboards e Relatorios

Prioridade principal: P1  
Modulo: `mod_dashboard`, `dw`, `frontend_core/dashboard`  
Objetivo: entregar visao executiva e operacional da campanha com KPIs, filtros, relatorios basicos e exportacoes controladas.

## Escopo MVP

- Dashboard inicial com KPIs.
- Cards de cadastro, liderancas, metas, eventos e demandas.
- Filtros por periodo, territorio, lider e perfil.
- Relatorios basicos em tela.
- Exportacao controlada para CSV/XLSX quando autorizada.
- Base preparada para tabelas DW ja existentes.

## Fora do MVP

- Power BI/Tableau embutido.
- Dashboards em tempo real.
- Relatorios PDF sofisticados.
- Cubos analiticos completos.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| DASH-001 | P1 | Backend | Mapear entidades `dw.indicador`, `indicador_valor`, `dashboard_configuracao`, `relatorio`, `relatorio_execucao`. | Models/schemas criados para leitura e configuracao basica. |
| DASH-002 | P1 | Backend | Criar endpoint `GET /dashboard/visao-geral`. | Retorna totais de cadastrados, lideres, liderados, demandas, eventos e metas. |
| DASH-003 | P1 | Backend | Criar filtro padrao de periodo. | KPIs aceitam `data_inicio` e `data_fim`. |
| DASH-004 | P1 | Backend | Criar filtro padrao de territorio. | KPIs respeitam escopo territorial e permissao. |
| DASH-005 | P1 | Backend | Criar filtro padrao de lider. | KPIs podem ser recortados por lideranca. |
| DASH-006 | P1 | Backend | Criar KPI de cadastros. | Retorna total, novos no periodo e incompletos/pendentes. |
| DASH-007 | P1 | Backend | Criar KPI de liderancas. | Retorna total de lideres, liderados e media por lider. |
| DASH-008 | P1 | Backend | Criar KPI de metas. | Retorna metas ativas, atingidas, em risco e percentual medio. |
| DASH-009 | P1 | Backend | Criar KPI de demandas. | Retorna pendentes, em andamento, concluidas e vencidas. |
| DASH-010 | P1 | Backend | Criar KPI de eventos. | Retorna eventos no periodo, realizados, cancelados e presenca registrada. |
| DASH-011 | P1 | Backend | Criar endpoint de aniversariantes. | Retorna aniversariantes do dia e do mes com permissao. |
| DASH-012 | P1 | Backend | Criar endpoint de datas comemorativas dos proximos 30 dias. | Retorna datas por territorio/categoria quando aplicavel. |
| DASH-013 | P1 | Backend | Criar relatorio de metas por lider. | Lista lider, meta, atual, percentual e risco. |
| DASH-014 | P1 | Backend | Criar relatorio de demandas por status/responsavel. | Lista agregados por status, categoria, responsavel e prazo. |
| DASH-015 | P1 | Backend | Criar relatorio de agenda diaria/mensal. | Lista eventos, convites, pautas e responsaveis. |
| DASH-016 | P1 | Backend | Criar relatorio de evolucao de cadastros. | Serie temporal por periodo e origem. |
| DASH-017 | P1 | Backend | Criar relatorio de ranking de lideres. | Ordena lideres por desempenho e filtros. |
| DASH-018 | P1 | Backend | Criar endpoint de exportacao controlada. | Exportacao exige permissao e registra `log_exportacao`. |
| DASH-019 | P1 | Backend | Criar cache simples para KPIs pesados. | Dashboard nao recalcula tudo em chamadas repetidas de curto intervalo. |
| DASH-020 | P1 | Frontend | Criar pagina inicial do dashboard. | Cards principais aparecem apos login. |
| DASH-021 | P1 | Frontend | Criar barra de filtros globais. | Periodo, territorio e lider alteram os cards. |
| DASH-022 | P1 | Frontend | Criar card de cadastros. | Mostra total, novos e pendentes. |
| DASH-023 | P1 | Frontend | Criar card de liderancas. | Mostra lideres, liderados e media. |
| DASH-024 | P1 | Frontend | Criar card de metas. | Mostra atingidas, em risco e percentual. |
| DASH-025 | P1 | Frontend | Criar card de demandas. | Mostra status principais e vencidas. |
| DASH-026 | P1 | Frontend | Criar card de eventos. | Mostra agenda do periodo e status. |
| DASH-027 | P1 | Frontend | Criar widgets de aniversariantes e datas. | Lista dia, mes e proximos 30 dias. |
| DASH-028 | P1 | Frontend | Criar tela de relatorios. | Usuario acessa relatorios de metas, demandas, agenda, cadastros e lideres. |
| DASH-029 | P1 | Frontend | Criar exportacao com justificativa. | Usuario informa finalidade antes de exportar dados sensiveis. |
| DASH-030 | P1 | QA | Testar dashboard por perfil. | Gestor ve consolidado e coordenador ve territorio permitido. |
| DASH-031 | P1 | QA | Testar exportacao auditada. | Exportacao cria log com filtros e finalidade. |
| DASH-032 | P2 | Jobs | Criar rotina de materializacao em `dw.indicador_valor`. | Indicadores historicos sao calculados por periodo. |
| DASH-033 | P2 | Jobs | Criar execucao agendada de relatorios. | Relatorios podem ser gerados por job e consultados depois. |
| DASH-034 | P2 | Backend | Criar configuracao de dashboard por perfil. | Widgets habilitados variam por perfil/tenant. |
| DASH-035 | P3 | Backend | Integrar dashboard externo de BI se aprovado. | Link/embed respeita tenant, seguranca e permissao. |

## Indicadores MVP

| Painel | Indicadores |
| --- | --- |
| Visao geral | Total de cadastrados, lideres, liderados, demandas, eventos, metas em risco. |
| Cadastro | Novos cadastros, pendentes de validacao, duplicidades abertas, completude. |
| Metas | Meta total, atual, percentual, ranking de lideres, metas abaixo de 70%. |
| Demandas | Pendentes, em andamento, concluidas, vencidas, por categoria e responsavel. |
| Agenda | Eventos por periodo, status, presenca, origem do convite, demandas geradas. |
| Relacionamento | Aniversariantes do dia/mes e datas comemorativas proximas. |

## Regras de negocio

- Dashboard deve sempre respeitar tenant, perfil e territorio.
- Exportacao deve ser mais restrita que visualizacao em tela.
- Dados sensiveis devem ser mascarados quando perfil nao exigir detalhe.
- Indicadores do MVP podem consultar tabelas operacionais, mas a arquitetura deve permitir migrar para DW.

## Entidades principais

- `dw.indicador`
- `dw.indicador_valor`
- `dw.dashboard_configuracao`
- `dw.relatorio`
- `dw.relatorio_execucao`
- `dw.fato_cadastro`
- `dw.fato_demanda`
- `dw.fato_evento`
- `dw.fato_meta_voto`
- `auditoria.log_exportacao`

## Definition of Done

- Dashboard inicial responde rapido em volume moderado.
- KPIs principais aparecem no frontend.
- Filtros globais funcionam e respeitam permissao.
- Relatorios basicos estao disponiveis.
- Exportacoes sao auditadas.
