# SPEC-06 - Metas de Votos, Rankings e Alertas

Prioridade principal: P1  
Modulo: `mod_metas`, `frontend_core/metas`  
Objetivo: permitir que a campanha defina, acompanhe e compare metas de votos por lider, equipe, territorio, comunidade, nucleo familiar ou campanha inteira.

## Escopo MVP

- Periodos de meta.
- Tipos de meta.
- Criacao de metas por lider e territorio.
- Vinculo flexivel de alvo da meta.
- Acompanhamento manual e calculado.
- Percentual de atingimento.
- Ranking basico de liderancas.
- Alerta inicial para meta abaixo de 70%.

## Fora do MVP

- Previsao automatica de risco com ML.
- Gamificacao avancada.
- Notificacoes em tempo real.
- Integracao com resultado eleitoral oficial.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| META-001 | P1 | Backend | Mapear entidades de metas. | Models/schemas para tipo, periodo, meta, alvo, acompanhamento, alerta e ranking. |
| META-002 | P1 | Backend | Criar CRUD de `tipo_meta_voto`. | Gestor administra tipos globais ou padrao do tenant conforme regra. |
| META-003 | P1 | Backend | Criar CRUD de `periodo_meta`. | Periodo tem inicio, fim, ciclo e eleicao quando aplicavel. |
| META-004 | P1 | Backend | Criar endpoint para criar meta. | Meta possui quantidade, periodo, tipo, status e responsavel. |
| META-005 | P1 | Backend | Criar endpoint para editar meta. | Alteracao registra auditoria. |
| META-006 | P1 | Backend | Criar endpoint para inativar/cancelar meta. | Meta cancelada nao entra nos calculos ativos. |
| META-007 | P1 | Backend | Implementar `meta_voto_alvo`. | Meta pode apontar para lideranca, territorio, equipe, comunidade, nucleo familiar ou pessoa. |
| META-008 | P1 | Backend | Validar alvo obrigatorio conforme tipo. | API rejeita meta por lider sem lideranca, por territorio sem territorio etc. |
| META-009 | P1 | Backend | Calcular pessoas vinculadas ao alvo. | Meta mostra base de eleitores/apoiadores associada. |
| META-010 | P1 | Backend | Criar acompanhamento manual da meta. | Usuario autorizado registra projecao, confirmacao e observacao. |
| META-011 | P1 | Backend | Calcular percentual atingido. | Retorno traz `quantidade_meta`, `quantidade_atual`, `percentual`. |
| META-012 | P1 | Backend | Criar regra de risco abaixo de 70%. | Meta abaixo do limiar gera situacao de risco. |
| META-013 | P1 | Backend | Criar `alerta_meta` basico. | Alerta e criado/atualizado quando meta fica abaixo do esperado. |
| META-014 | P1 | Backend | Criar endpoint `GET /metas/resumo`. | Retorna totais, metas em risco e percentuais por recorte. |
| META-015 | P1 | Backend | Criar endpoint de ranking de liderancas. | Ranking ordena por atingimento, cadastros e engajamento basico. |
| META-016 | P1 | Backend | Criar job de recalculo de ranking. | Job atualiza `meta.ranking_lideranca`. |
| META-017 | P1 | Backend | Criar filtro por territorio, lider, periodo e status. | Listagens de meta respeitam filtros. |
| META-018 | P1 | Frontend | Criar tela de metas. | Lista metas com filtros e percentuais. |
| META-019 | P1 | Frontend | Criar formulario de meta. | Usuario define tipo, periodo, alvo, quantidade e responsavel. |
| META-020 | P1 | Frontend | Criar detalhe de meta. | Exibe historico, alvo, progresso e alertas. |
| META-021 | P1 | Frontend | Criar componente de progresso de meta. | Barra/indicador mostra percentual e risco. |
| META-022 | P1 | Frontend | Criar ranking de liderancas. | Tabela mostra lider, meta, atual, percentual e risco. |
| META-023 | P1 | Frontend | Criar alerta visual para metas abaixo de 70%. | Metas em risco ficam destacadas sem depender so de cor. |
| META-024 | P1 | Frontend | Exibir resumo de metas no dashboard. | Cards mostram metas ativas, atingidas e em risco. |
| META-025 | P1 | QA | Testar criacao de meta por lider. | Meta por lider calcula progresso esperado. |
| META-026 | P1 | QA | Testar criacao de meta por territorio. | Meta por territorio respeita filtro territorial. |
| META-027 | P1 | QA | Testar alerta abaixo de 70%. | Alerta aparece quando percentual fica abaixo do limiar. |
| META-028 | P2 | Jobs | Criar recalculo automatico por mudanca em cadastro. | Novo eleitor vinculado atualiza acompanhamento ou ranking. |
| META-029 | P2 | Backend | Criar configuracao de limiar de risco por tenant. | Tenant pode alterar 70% para outro limiar autorizado. |
| META-030 | P3 | Backend | Criar score preditivo de risco. | Modelo estima risco com base em historico e engajamento. |

## Regras de negocio

- Meta deve ter periodo valido.
- Meta deve ter pelo menos um alvo.
- Meta global pode nao ter alvo especifico alem do tenant/campanha.
- Ranking deve ser reprodutivel e documentado.
- Confirmacao operacional nao deve ser confundida com comprovacao oficial de voto.
- Alertas de risco devem ser auditaveis quando gerarem acao operacional.

## Entidades principais

- `meta.tipo_meta_voto`
- `meta.periodo_meta`
- `meta.meta_voto`
- `meta.meta_voto_alvo`
- `meta.acompanhamento_meta`
- `meta.alerta_meta`
- `meta.ranking_lideranca`
- `cadastro.lideranca`
- `territorio.territorio`

## Definition of Done

- Gestor cria metas por lider e territorio.
- Lider/coordenador visualiza metas conforme permissao.
- Percentual de atingimento e calculado.
- Ranking basico funciona.
- Metas em risco aparecem no dashboard e geram alerta inicial.
