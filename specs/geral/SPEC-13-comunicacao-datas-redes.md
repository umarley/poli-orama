# SPEC-13 - Comunicacao, Datas e Redes Sociais

Prioridade principal: P2/P3  
Modulo: `comunicacao`, `global`, `frontend_core/comunicacao`  
Objetivo: apoiar relacionamento politico com registro de interacoes, datas comemorativas, consentimento, campanhas de comunicacao e monitoramento social permitido.

## Escopo MVP reduzido

- Aniversariantes no dashboard.
- Datas comemorativas globais.
- Registro manual de interacao no detalhe da pessoa.

## Escopo P2

- Campanhas de comunicacao segmentadas.
- Mensagens manuais e historico.
- Consentimento e preferencias de contato.
- Relatorios de interacoes.

## Escopo P3

- Integracoes oficiais com WhatsApp/Instagram quando viaveis.
- Monitoramento de publicacoes e engajamento social.
- Automacoes e segmentacoes avancadas.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| COM-001 | P1 | Backend | Mapear `categoria_data_comemorativa` e `data_comemorativa`. | Datas globais podem ser consultadas. |
| COM-002 | P1 | Backend | Criar endpoint de aniversariantes do dia/mes. | Retorna pessoas permitidas por tenant e territorio. |
| COM-003 | P1 | Backend | Criar endpoint de datas proximas. | Retorna datas dos proximos 30 dias por categoria/territorio. |
| COM-004 | P1 | Backend | Mapear `interacao`, `tipo_interacao` e `canal_comunicacao`. | Interacoes manuais podem ser persistidas. |
| COM-005 | P1 | Backend | Criar CRUD de tipo de interacao. | Tipos como ligacao, WhatsApp, visita, reuniao, e-mail. |
| COM-006 | P1 | Backend | Criar CRUD de canal de comunicacao. | Canais ficam configuraveis. |
| COM-007 | P1 | Backend | Criar endpoint para registrar interacao em pessoa. | Interacao fica no historico da pessoa. |
| COM-008 | P1 | Frontend | Exibir aniversariantes no dashboard. | Widget mostra dia/mes com filtros. |
| COM-009 | P1 | Frontend | Exibir datas comemorativas proximas. | Widget mostra proximos 30 dias. |
| COM-010 | P1 | Frontend | Criar aba de interacoes no detalhe da pessoa. | Usuario registra e visualiza historico manual. |
| COM-011 | P1 | QA | Testar registro de interacao. | Interacao respeita tenant, permissao e auditoria quando sensivel. |
| COM-012 | P2 | Backend | Mapear `consentimento_comunicacao`. | Preferencia, base legal e opt-out ficam registrados. |
| COM-013 | P2 | Backend | Criar endpoint de consentimento. | Usuario autorizado registra consentimento ou opt-out. |
| COM-014 | P2 | Frontend | Criar UI de preferencias de contato. | Detalhe da pessoa mostra consentimento e canais permitidos. |
| COM-015 | P2 | Backend | Mapear `campanha_comunicacao` e `mensagem_comunicacao`. | Campanhas e mensagens podem ser salvas. |
| COM-016 | P2 | Backend | Criar CRUD de campanha de comunicacao. | Campanha tem segmento, canal, objetivo, status e responsavel. |
| COM-017 | P2 | Backend | Criar segmentacao por tags, comunidades, territorio e lider. | Campanha calcula publico-alvo permitido. |
| COM-018 | P2 | Backend | Criar registro manual de mensagem individual/lote. | Mensagens ficam no historico com canal e status. |
| COM-019 | P2 | Frontend | Criar tela de campanhas de comunicacao. | Usuario cria, edita e acompanha campanhas manuais. |
| COM-020 | P2 | Frontend | Criar seletor de publico-alvo. | Tags, comunidades, territorios e lideres filtram destinatarios. |
| COM-021 | P2 | QA | Testar opt-out. | Pessoa com opt-out nao entra em campanha daquele canal. |
| COM-022 | P3 | Backend | Mapear perfil social monitorado. | Perfis sociais podem ser associados a pessoa/lideranca/campanha. |
| COM-023 | P3 | Backend | Mapear publicacao social e engajamento. | Postagens e metricas podem ser registradas manualmente ou por API. |
| COM-024 | P3 | Backend | Avaliar integracao oficial Instagram. | Documento tecnico define limites, permissoes e riscos. |
| COM-025 | P3 | Backend | Avaliar integracao oficial WhatsApp. | Documento tecnico define API, consentimento e modelo operacional. |
| COM-026 | P3 | Jobs | Criar ingestao de publicacoes quando permitido. | Job registra publicacoes e metricas conforme credenciais aprovadas. |
| COM-027 | P3 | Frontend | Criar painel de engajamento social. | Mostra alcance, curtidas, comentarios, compartilhamentos e tendencia. |

## Regras de negocio

- Comunicacao deve respeitar consentimento, finalidade e opt-out.
- Dados de religiao, opiniao politica e perfil social exigem cuidado juridico e permissao.
- Integracoes com WhatsApp e Instagram dependem de APIs oficiais e politicas vigentes.
- Registro manual deve ficar claramente diferenciado de captura automatica.
- Nao enviar CPF, telefone completo ou dados sensiveis para analytics externo.

## Entidades principais

- `global.categoria_data_comemorativa`
- `global.data_comemorativa`
- `comunicacao.canal_comunicacao`
- `comunicacao.tipo_interacao`
- `comunicacao.interacao`
- `comunicacao.campanha_comunicacao`
- `comunicacao.mensagem_comunicacao`
- `comunicacao.consentimento_comunicacao`
- `comunicacao.perfil_social_monitorado`
- `comunicacao.publicacao_social`
- `comunicacao.engajamento_social`

## Definition of Done

- MVP exibe aniversariantes e datas relevantes.
- Interacoes manuais ficam registradas por pessoa.
- P2 controla consentimento e campanhas manuais.
- P3 so integra redes sociais apos avaliacao legal, tecnica e de API.
