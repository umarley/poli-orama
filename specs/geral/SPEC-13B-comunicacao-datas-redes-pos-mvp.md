# SPEC-13B - Comunicacao, Datas e Redes Sociais Pos-MVP

Prioridade principal: P2/P3  
Modulo: `comunicacao`, `backend_jobs_celery`, `frontend_core/comunicacao`  
Origem: tarefas COM-012 em diante migradas da `SPEC-13-comunicacao-datas-redes.md` apos recorte MVP.

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

## Regras de negocio mantidas

- Comunicacao deve respeitar consentimento, finalidade e opt-out.
- Dados de religiao, opiniao politica e perfil social exigem cuidado juridico e permissao.
- Integracoes com WhatsApp e Instagram dependem de APIs oficiais e politicas vigentes.
- Registro manual deve ficar claramente diferenciado de captura automatica.
- Nao enviar CPF, telefone completo ou dados sensiveis para analytics externo.
