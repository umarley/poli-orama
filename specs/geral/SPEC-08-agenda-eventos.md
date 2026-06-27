# SPEC-08 - Agenda e Eventos

Prioridade principal: P1  
Modulo: `mod_agenda`, `frontend_core/agenda`  
Objetivo: controlar agenda politica, eventos, convites, pautas, presenca, liderancas envolvidas e demandas geradas.

## Escopo MVP

- Tipos e status de evento.
- Cadastro de evento com data, local, responsavel e territorio.
- Participantes e liderancas envolvidas.
- Registro de convite e pauta.
- Registro de presenca do parlamentar/representante e numero de presentes.
- Criacao de demanda a partir de evento.
- Calendario simples.

## Fora do MVP

- Sincronizacao com Google Calendar/Outlook.
- OCR automatico de convites.
- Notificacoes automaticas.
- Check-in por QR Code.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| AGE-001 | P1 | Backend | Mapear entidades de agenda. | Models/schemas para tipo, status, evento, participante, lideranca, convite, pauta e presenca. |
| AGE-002 | P1 | Backend | Criar CRUD de `tipo_evento`. | Gestor administra tipos como politico, religioso, comunitario, partidario etc. |
| AGE-003 | P1 | Backend | Criar CRUD de `status_evento`. | Status planejado, confirmado, realizado, cancelado e remarcado estao disponiveis. |
| AGE-004 | P1 | Backend | Criar endpoint `GET /agenda/eventos`. | Lista eventos com filtros por periodo, territorio, lider, tipo e status. |
| AGE-005 | P1 | Backend | Criar endpoint `POST /agenda/eventos`. | Evento e criado com data, hora, local, responsavel e territorio. |
| AGE-006 | P1 | Backend | Criar endpoint de detalhe de evento. | Retorna participantes, liderancas, convites, pautas e presenca. |
| AGE-007 | P1 | Backend | Criar endpoint de edicao de evento. | Atualizacao registra auditoria. |
| AGE-008 | P1 | Backend | Criar endpoint para cancelar evento. | Status muda para cancelado com motivo. |
| AGE-009 | P1 | Backend | Vincular evento a territorio. | Evento aparece em filtros territoriais. |
| AGE-010 | P1 | Backend | Vincular liderancas ao evento. | Lideres/coordenadores envolvidos ficam associados. |
| AGE-011 | P1 | Backend | Vincular participantes ao evento. | Pessoas cadastradas podem ser participantes com papel e presenca. |
| AGE-012 | P1 | Backend | Registrar convite. | Convite possui origem, quem indicou, arquivo opcional e status. |
| AGE-013 | P1 | Backend | Registrar pauta do evento. | Pautas possuem tema, descricao e encaminhamento. |
| AGE-014 | P1 | Backend | Registrar presenca do parlamentar ou representante. | Presenca e numero estimado de presentes ficam salvos. |
| AGE-015 | P1 | Backend | Criar demanda a partir do evento. | Demanda herda pessoa, territorio, origem e evento quando informado. |
| AGE-016 | P1 | Backend | Criar resumo da agenda por periodo. | Retorna total por dia, status e tipo. |
| AGE-017 | P1 | Backend | Aplicar filtro de permissao territorial. | Coordenador ve eventos do seu escopo. |
| AGE-018 | P1 | Frontend | Criar tela de calendario. | Usuario alterna entre visao mensal, semanal ou lista simples. |
| AGE-019 | P1 | Frontend | Criar tela/listagem de eventos. | Filtros por periodo, territorio, lider, tipo e status. |
| AGE-020 | P1 | Frontend | Criar formulario de evento. | Usuario cadastra titulo, descricao, data, local, territorio, responsavel e tipo. |
| AGE-021 | P1 | Frontend | Criar detalhe de evento com abas. | Abas para dados, participantes, liderancas, convites, pautas, presenca e demandas. |
| AGE-022 | P1 | Frontend | Criar cadastro de participantes. | Usuario busca pessoa e adiciona ao evento. |
| AGE-023 | P1 | Frontend | Criar cadastro de liderancas envolvidas. | Usuario adiciona lider/coordenador ao evento. |
| AGE-024 | P1 | Frontend | Criar registro de convite. | Usuario informa origem e anexa arquivo se modulo de arquivos estiver disponivel. |
| AGE-025 | P1 | Frontend | Criar registro de pauta. | Usuario informa pauta e encaminhamentos. |
| AGE-026 | P1 | Frontend | Criar registro de presenca. | Usuario informa presenca do parlamentar/representante e numero de presentes. |
| AGE-027 | P1 | Frontend | Criar acao de criar demanda a partir do evento. | Formulario de demanda abre com evento e origem preenchidos. |
| AGE-028 | P1 | QA | Testar CRUD de evento. | Evento criado aparece no calendario e detalhe. |
| AGE-029 | P1 | QA | Testar filtros territoriais. | Evento fora do territorio permitido nao aparece. |
| AGE-030 | P1 | QA | Testar demanda originada em evento. | Demanda criada guarda `evento_id`. |
| AGE-031 | P2 | Jobs | Criar lembretes de eventos proximos. | Job gera notificacao ou alerta interno conforme config. |
| AGE-032 | P2 | Backend | Criar exportacao de agenda diaria/mensal. | Usuario autorizado exporta agenda com filtros. |
| AGE-033 | P3 | Jobs | Criar NLP de pautas e convites. | Sistema sugere temas e demandas recorrentes. |

## Regras de negocio

- Evento deve ter data/hora e responsavel.
- Evento pode ter local ainda sem coordenada.
- Evento pode gerar uma ou mais demandas.
- Convites e pautas podem existir como metadados mesmo sem anexo.
- Eventos devem respeitar permissao territorial e tenant.

## Entidades principais

- `agenda.tipo_evento`
- `agenda.status_evento`
- `agenda.evento`
- `agenda.evento_participante`
- `agenda.evento_lideranca`
- `agenda.convite`
- `agenda.pauta_evento`
- `agenda.presenca_evento`
- `demanda.demanda`
- `arquivo.anexo`

## Definition of Done

- Usuario cadastra e acompanha eventos.
- Calendario/lista funciona com filtros.
- Participantes, liderancas, convites, pautas e presenca ficam registrados.
- Demandas podem ser criadas a partir de eventos.
- Dashboard recebe indicadores basicos de agenda.
