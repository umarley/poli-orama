# Integração com Google Agenda

## Visão geral

Cada agenda do Poliorama pode ser vinculada, de forma independente, a uma agenda já existente na
conta Google do usuário. O vínculo aceita três direções:

- `bidirecional`: alterações novas dos dois lados são conciliadas;
- `sistema_google`: o Poliorama publica e atualiza compromissos no Google;
- `google_sistema`: o Poliorama importa e atualiza compromissos do Google.

A sincronização usa `event.id`, `etag`, datas de atualização e `nextSyncToken` para ser incremental e
idempotente. Um `syncToken` expirado (HTTP 410) dispara uma leitura completa segura. Eventos criados
pelo sistema recebem propriedades privadas `poliorama_evento_id` e `poliorama_tenant_id`, o que
permite recuperar o vínculo sem duplicar compromissos.

## Configuração no Google Cloud

1. Crie ou selecione um projeto no Google Cloud Console.
2. Ative a **Google Calendar API**.
3. Configure a tela de consentimento OAuth e publique ou cadastre os usuários de teste.
4. Crie uma credencial OAuth 2.0 do tipo **Aplicativo da Web**.
5. Cadastre exatamente a URI informada em `GOOGLE_CALENDAR_REDIRECT_URI`, por exemplo:
   `https://api.exemplo.com/api/v1/agenda/google/oauth/callback`.
6. Se o aplicativo estiver em produção, configure domínio autorizado, política de privacidade e os
   requisitos de verificação de escopos exigidos pelo Google.

Referências oficiais: [OAuth 2.0 para aplicações Web](https://developers.google.com/identity/protocols/oauth2/web-server),
[Calendar API v3](https://developers.google.com/workspace/calendar/api/v3/reference) e
[sincronização incremental](https://developers.google.com/workspace/calendar/api/guides/sync).

## Variáveis de ambiente do backend

```env
GOOGLE_CALENDAR_CLIENT_ID=cliente.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=segredo-do-cliente
GOOGLE_CALENDAR_REDIRECT_URI=https://api.exemplo.com/api/v1/agenda/google/oauth/callback
GOOGLE_CALENDAR_FRONTEND_URL=https://app.exemplo.com/agenda
GOOGLE_CALENDAR_ENCRYPTION_KEY=uma-chave-aleatoria-exclusiva-com-32-ou-mais-caracteres
```

Use uma chave de criptografia exclusiva por ambiente e mantenha-a em cofre de segredos. A troca da
chave exige reconectar as contas Google existentes. Access tokens, refresh tokens e o verificador
PKCE são criptografados antes de serem persistidos; o estado OAuth é armazenado apenas como SHA-256,
expira em dez minutos e é consumido uma única vez.

Os escopos solicitados são:

- `openid email`, para identificar a conta autorizadora;
- `calendar.calendarlist.readonly`, para listar as agendas disponíveis;
- `calendar.events`, para sincronizar eventos somente na agenda escolhida.

## Banco de dados

Execute as migrations pelo mecanismo já adotado pelo projeto. O DDL desta entrega está em
`database/migrations/049 - agendas_classificacao_permissoes_google_calendar.sql`.

```powershell
cd app_saas/database
python scripts/run_migrations.py
```

A migration:

- cria agendas, permissões por usuário e tabelas de integração Google;
- cria uma agenda pública padrão por tenant e move os eventos existentes para ela;
- adiciona índices, auditoria temporal e isolamento RLS por tenant;
- cadastra as novas permissões RBAC para gestores.

## Operação

1. Acesse **Agenda > Agendas**.
2. Crie ou edite uma agenda com natureza, frente/comunidade, tipo, visibilidade e cor.
3. Em uma agenda restrita, abra **Usuários** e conceda apenas as ações necessárias.
4. Em **Google Agenda**, conecte a conta, selecione uma agenda com acesso de escrita e escolha a
   direção da sincronização.
5. Use **Sincronizar agora**. O resumo informa itens enviados, importados, atualizados, removidos e
   erros individuais.

Para importação Google → sistema, o usuário que autorizou a conta deve estar vinculado a uma pessoa
do cadastro, pois todo compromisso do domínio exige um responsável. Sem esse vínculo, o evento é
ignorado e aparece no resumo de erros sem interromper os demais itens.

## Regras de conflito e falhas

- Em sincronização bidirecional, alterações Google são lidas antes do envio local; cada lado só é
  reprocessado quando sua data de atualização avança desde a última sincronização.
- Exclusões e cancelamentos locais removem o evento correspondente no Google.
- Exclusões Google cancelam o compromisso importado, preservando histórico e auditoria no sistema.
- Falhas de autenticação, revogação, quota, rede ou dados inválidos são apresentadas ao usuário e
  armazenadas na integração; tokens nunca são incluídos nos erros ou respostas da API.
- A associação é única por agenda do sistema e por par conta/calendário Google, evitando publicação
  duplicada acidental.

Em instalações com grande volume, o endpoint
`POST /api/v1/agenda/agendas/{agenda_id}/google/sincronizar` pode ser acionado por um agendador
autenticado em lotes. Como a leitura é incremental e paginada, o custo cresce com as alterações desde
a última execução, não com todo o histórico.
