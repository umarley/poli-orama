# SPEC-09 - Demandas e Atendimentos

Status: concluida no MVP, com aprimoramentos transferidos para a SPEC-22  
Prioridade principal: P1  
Modulo: `mod_demandas`, `frontend_core/demandas`  
Objetivo: controlar solicitacoes, pedidos, atendimentos, responsaveis, prazos, resultados, status e historico de movimentacoes.

## Escopo MVP

- Categorias, status, prioridade, origem e resultado.
- Cadastro de demanda.
- Vinculo com pessoa solicitante, lider, territorio e evento.
- Atribuicao de responsavel.
- Controle de prazo.
- Atendimento e movimentacoes.
- Filtros e indicadores basicos.

## Fora do MVP

- Classificacao automatica por NLP.
- SLA sofisticado por categoria.
- Integracao com sistemas externos de atendimento.
- Comunicacao automatica com solicitante.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| DEM-001 | P1 | Backend | Mapear entidades de demanda. | Models/schemas para categoria, status, prioridade, origem, resultado, demanda, responsavel, atendimento e movimentacao. |
| DEM-002 | P1 | Backend | Criar CRUD de `categoria_demanda`. | Gestor administra categorias como saude, educacao, infraestrutura etc. |
| DEM-003 | P1 | Backend | Criar CRUD de `status_demanda`. | Status pendente, em andamento, concluida, cancelada, nao atendida e parcialmente atendida estao disponiveis. |
| DEM-004 | P1 | Backend | Criar CRUD de `prioridade_demanda`. | Prioridades baixa, media, alta e urgente ou equivalentes. |
| DEM-005 | P1 | Backend | Criar CRUD de `origem_demanda`. | Origens evento, ligacao, WhatsApp, cadastro manual, lider, comunidade e importacao. |
| DEM-006 | P1 | Backend | Criar CRUD de `resultado_atendimento`. | Resultados solucionado, parcialmente atendido e nao atendido. |
| DEM-007 | P1 | Backend | Criar endpoint `GET /demandas`. | Lista com filtros por status, categoria, responsavel, territorio, origem, periodo e lider. |
| DEM-008 | P1 | Backend | Criar endpoint `POST /demandas`. | Demanda e criada com pessoa solicitante, descricao, categoria, origem e territorio. |
| DEM-009 | P1 | Backend | Criar endpoint de detalhe da demanda. | Retorna dados, solicitante, atendimentos, movimentacoes e anexos. |
| DEM-010 | P1 | Backend | Criar endpoint de edicao da demanda. | Atualizacao registra auditoria e movimentacao quando status/responsavel/prazo muda. |
| DEM-011 | P1 | Backend | Vincular demanda a evento. | Demanda originada em evento guarda `evento_id`. |
| DEM-012 | P1 | Backend | Vincular demanda a lider/responsavel pela indicacao. | Relatorio por lider consegue contar demandas geradas. |
| DEM-013 | P1 | Backend | Vincular demanda a territorio. | Demanda aparece em filtros territoriais. |
| DEM-014 | P1 | Backend | Criar atribuicao de responsavel. | Responsavel pode ser pessoa, usuario, setor ou area. |
| DEM-015 | P1 | Backend | Criar controle de prazo. | Demanda com prazo vencido e identificada. |
| DEM-016 | P1 | Backend | Criar atendimento vinculado a demanda. | Atendimento possui responsavel, data, prazo, resultado e observacao. |
| DEM-017 | P1 | Backend | Criar movimentacao automatica. | Mudancas relevantes criam historico com usuario e data. |
| DEM-018 | P1 | Backend | Criar endpoint de resumo de demandas. | Retorna total por status, categoria, territorio e responsavel. |
| DEM-019 | P1 | Backend | Aplicar filtro de permissao territorial. | Usuarios veem apenas demandas permitidas. |
| DEM-020 | P1 | Frontend | Criar tela de demandas. | Tabela com filtros, status e prazos. |
| DEM-021 | P1 | Frontend | Criar formulario de demanda. | Usuario busca/cadastra solicitante e informa categoria, origem, descricao e territorio. |
| DEM-022 | P1 | Frontend | Criar detalhe de demanda. | Abas para dados, atendimentos, movimentacoes e anexos. |
| DEM-023 | P1 | Frontend | Criar alteracao rapida de status. | Usuario autorizado muda status com observacao obrigatoria. |
| DEM-024 | P1 | Frontend | Criar atribuicao de responsavel. | Usuario atribui responsavel e prazo. |
| DEM-025 | P1 | Frontend | Criar registro de atendimento. | Usuario registra acao de atendimento e resultado. |
| DEM-026 | P1 | Frontend | Criar destaque de demandas vencidas. | Lista diferencia demandas com prazo vencido sem depender so de cor. |
| DEM-027 | P1 | Frontend | Criar resumo no dashboard. | Cards mostram pendentes, em andamento, concluidas e vencidas. |
| DEM-028 | P1 | QA | Testar fluxo completo de demanda. | Cria demanda, atribui responsavel, registra atendimento e conclui. |
| DEM-029 | P1 | QA | Testar movimentacao automatica. | Mudanca de status cria historico. |
| DEM-030 | P1 | QA | Testar filtro territorial. | Usuario sem acesso nao ve demanda de outro territorio. |
| DEM-031 | P2 | Backend | Criar exportacao de demandas por filtro. | Exportacao registra finalidade e auditoria. |
| DEM-032 | P2 | Jobs | Criar alertas de prazos vencendo/vencidos. | Job gera alerta para responsaveis conforme regra. |
| DEM-033 | P3 | Jobs | Criar classificacao automatica por NLP. | Descricao sugere categoria e prioridade. |

## Regras de negocio

- Demanda deve ter solicitante ou origem claramente identificada.
- Toda mudanca de status, responsavel, prazo ou resultado deve gerar movimentacao.
- Prazo vencido deve ser calculado pelo backend.
- Demanda pode nascer de evento, contato, importacao, lider ou cadastro manual.
- Encerramento deve exigir resultado.

## Entidades principais

- `demanda.categoria_demanda`
- `demanda.status_demanda`
- `demanda.prioridade_demanda`
- `demanda.origem_demanda`
- `demanda.resultado_atendimento`
- `demanda.demanda`
- `demanda.responsavel_atendimento`
- `demanda.atendimento`
- `demanda.movimentacao_demanda`
- `agenda.evento`
- `cadastro.pessoa`
- `territorio.territorio`

## Definition of Done

- Usuario registra e acompanha demandas.
- Responsaveis, prazos e atendimentos funcionam.
- Historico de movimentacoes e auditavel.
- Demandas aparecem em dashboard e relatorios basicos.
- Filtros por status, categoria, territorio, lider e responsavel funcionam.
