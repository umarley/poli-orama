# SPEC-02 - Tenants, Planos e Onboarding

Prioridade principal: P0  
Modulo: `tenants`, `public`, `auth`, `site_publico`  
Objetivo: permitir que o SaaS represente clientes/campanhas/candidatos, seus planos, configuracoes e ativacao inicial com isolamento logico por tenant.

## Escopo MVP

- CRUD administrativo de tenants.
- Consulta publica de planos ativos.
- Configuracao inicial do tenant.
- Fluxo manual ou semiautomatico de onboarding.
- Preparacao para checkout e ativacao futura.

## Fora do MVP

- Billing recorrente completo.
- Webhooks reais de pagamento se o provedor nao estiver definido.
- Upgrade/downgrade automatico de plano.
- Provisionamento multi-regiao.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| TEN-001 | P0 | Backend | Mapear entidades `plano_assinatura`, `tenant` e `tenant_configuracao`. | Models/schemas representam colunas essenciais do banco. |
| TEN-002 | P0 | Backend | Criar endpoint publico `GET /api/public/planos`. | Retorna apenas planos ativos em ordem comercial. |
| TEN-003 | P0 | Backend | Criar endpoint admin para listar tenants. | Gestor SaaS consegue listar tenants com filtros por status/plano. |
| TEN-004 | P0 | Backend | Criar endpoint admin para criar tenant. | Tenant novo recebe status inicial e configuracao padrao. |
| TEN-005 | P0 | Backend | Criar endpoint admin para editar dados basicos do tenant. | Nome, slug, status e plano podem ser atualizados com auditoria. |
| TEN-006 | P0 | Backend | Criar regra de unicidade de slug do tenant. | API rejeita slug duplicado com erro claro. |
| TEN-007 | P0 | Backend | Criar service para carregar configuracao do tenant atual. | Endpoints privados conseguem obter config do tenant logado. |
| TEN-008 | P0 | Backend | Criar seed inicial de planos comerciais. | Ambiente local possui planos `essencial`, `profissional`, `operacao`, `enterprise` ou equivalentes. |
| TEN-009 | P0 | Backend | Criar endpoint `GET /me/tenant`. | Usuario autenticado visualiza tenant e configuracoes permitidas. |
| TEN-010 | P0 | Backend | Criar fluxo de ativacao manual de tenant. | Tenant pode mudar de pendente para ativo por usuario autorizado. |
| TEN-011 | P0 | Backend | Criar bloqueio para tenant inativo. | Login ou chamadas privadas falham para tenant suspenso/inativo. |
| TEN-012 | P1 | Backend | Criar endpoint publico `POST /api/public/leads`. | Lead comercial e consentimento sao registrados. |
| TEN-013 | P1 | Backend | Criar endpoint publico `POST /api/public/contratacoes`. | Pre-cadastro cria solicitacao pendente sem ativar tenant automaticamente. |
| TEN-014 | P1 | Backend | Criar endpoint placeholder `POST /api/public/checkout/session`. | Retorna erro controlado ou URL sandbox conforme configuracao. |
| TEN-015 | P1 | Backend | Criar idempotencia basica para contratacao/checkout. | Reenvio do mesmo payload nao cria duplicidade indevida. |
| TEN-016 | P1 | Backend | Enviar notificacao interna quando lead ou contratacao for criada. | E-mail/log/evento operacional e gerado conforme config. |
| TEN-017 | P1 | Frontend | Criar tela admin de tenants. | Lista, cria e edita tenant conforme permissoes. |
| TEN-018 | P1 | Frontend | Criar tela de configuracoes do tenant. | Usuario autorizado ve nome publico, preferencias e parametros basicos. |
| TEN-019 | P1 | Frontend | Exibir tenant atual no shell autenticado. | Header/sidebar mostram campanha atual quando aplicavel. |
| TEN-020 | P1 | Frontend | Tratar tenant inativo/suspenso. | Interface mostra mensagem clara e bloqueia area logada. |
| TEN-021 | P1 | Site publico | Consumir planos estaticos ou API publica. | Pagina de planos reflete plano ativo e CTA correto. |
| TEN-022 | P1 | Site publico | Enviar lead para backend publico. | Formulario de demo/contato registra sucesso e erro. |
| TEN-023 | P1 | Site publico | Enviar pre-cadastro de contratacao. | Formulario `contratar` gera registro no backend. |
| TEN-024 | P2 | Backend | Integrar webhook do provedor de pagamento escolhido. | Pagamento aprovado ativa assinatura conforme evento confiavel. |
| TEN-025 | P2 | Backend | Criar rotina de suspensao por inadimplencia. | Tenant fica bloqueado quando status comercial exigir. |
| TEN-026 | P2 | Frontend | Criar tela de assinatura e limites do plano. | Gestor visualiza limites contratados e uso atual. |

## Regras de negocio

- Tenant e a unidade principal de isolamento.
- Dados privados devem sempre estar vinculados ao tenant.
- Criacao de tenant por checkout so deve ocorrer apos confirmacao confiavel de pagamento ou aprovacao comercial.
- Site publico nao processa dados de cartao.
- Leads e contratacoes devem registrar origem UTM quando enviada.

## Entidades principais

- `public.plano_assinatura`
- `public.tenant`
- `public.tenant_configuracao`
- `auth.usuario`
- `auditoria.log_auditoria`

## Definition of Done

- Plano ativo pode ser lido publicamente.
- Tenant pode ser criado, ativado, suspenso e consultado.
- Tenant inativo nao acessa areas privadas.
- Leads e contratacoes ficam persistidos com consentimento e origem.
- Acoes administrativas geram auditoria.
