# SPEC-03 - Autenticacao, RBAC, RLS e Auditoria

Prioridade principal: P0  
Modulo: `core`, `auth`, `auditoria`  
Objetivo: proteger dados politicos e pessoais com login seguro, permissoes por perfil, escopo territorial, isolamento por tenant e trilha de auditoria.

## Escopo MVP

- Login com e-mail/senha.
- JWT com `tenant_id`, `usuario_id` e perfis.
- Refresh token ou sessao controlada.
- Perfis basicos: gestor, coordenador territorial, lider, telefonista, administrativo.
- Permissoes por modulo/acao.
- Injecao do tenant atual na sessao do banco para RLS.
- Auditoria de criacao, edicao, exclusao, acesso sensivel e exportacao.

## Fora do MVP

- MFA obrigatorio.
- SSO corporativo.
- Politicas complexas ABAC.
- Gestao refinada de dispositivos.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| AUTH-001 | P0 | Backend | Mapear entidades `usuario`, `perfil_acesso`, `permissao`, `usuario_perfil`, `perfil_permissao`, `sessao_usuario`. | Models e schemas cobrem campos necessarios para login e permissao. |
| AUTH-002 | P0 | Backend | Implementar hash de senha seguro. | Senha nunca e armazenada em texto claro. |
| AUTH-003 | P0 | Backend | Criar endpoint `POST /auth/login`. | Credenciais validas retornam token e dados do usuario. |
| AUTH-004 | P0 | Backend | Criar endpoint `POST /auth/logout`. | Sessao/token fica invalidado quando aplicavel. |
| AUTH-005 | P0 | Backend | Criar endpoint `GET /auth/me`. | Retorna usuario, tenant, perfis e permissoes efetivas. |
| AUTH-006 | P0 | Backend | Criar dependencia `get_current_user`. | Endpoints privados bloqueiam chamada sem token. |
| AUTH-007 | P0 | Backend | Criar dependencia `get_db_session` com `SET LOCAL app.current_tenant_id`. | Queries privadas respeitam tenant atual. |
| AUTH-008 | P0 | Backend | Validar RLS em endpoints privados. | Usuario de um tenant nao acessa registro de outro tenant em teste. |
| AUTH-009 | P0 | Backend | Criar decorator/dependencia de permissao por modulo e acao. | Endpoint retorna 403 quando usuario nao tem permissao. |
| AUTH-010 | P0 | Backend | Criar seed de perfis basicos e permissoes iniciais. | Ambiente local tem perfis prontos para teste. |
| AUTH-011 | P0 | Backend | Implementar CRUD de usuarios por gestor autorizado. | Gestor cria, edita, ativa/inativa e associa perfis. |
| AUTH-012 | P0 | Backend | Implementar reset manual de senha por gestor autorizado. | Nova senha temporaria ou link controlado pode ser emitido. |
| AUTH-013 | P0 | Backend | Criar politica de senha minima. | API rejeita senha fraca conforme regra documentada. |
| AUTH-014 | P0 | Backend | Criar registro de sessao em `auth.sessao_usuario`. | Login cria sessao com IP, user-agent e expiracao. |
| AUTH-015 | P0 | Backend | Criar auditoria generica em `auditoria.log_auditoria`. | Mutacoes sensiveis registram usuario, tenant, entidade, acao e data. |
| AUTH-016 | P0 | Backend | Criar helper para auditoria em services. | Services conseguem registrar auditoria de forma padronizada. |
| AUTH-017 | P0 | Backend | Criar auditoria de exportacao em `auditoria.log_exportacao`. | Exportacao registra filtros, finalidade, volume e usuario. |
| AUTH-018 | P1 | Backend | Implementar `politica_acesso_territorial`. | Coordenador ve apenas territorios permitidos em endpoints preparados. |
| AUTH-019 | P1 | Backend | Criar endpoint para configurar acesso territorial do usuario. | Gestor associa usuario a territorio com papel de visualizar/administrar. |
| AUTH-020 | P1 | Frontend | Criar tela de login. | Usuario entra e e redirecionado para dashboard. |
| AUTH-021 | P1 | Frontend | Criar protecao de rotas autenticadas. | Rotas privadas redirecionam para login sem token. |
| AUTH-022 | P1 | Frontend | Criar store de sessao e refresh controlado. | Sessao permanece valida durante uso normal. |
| AUTH-023 | P1 | Frontend | Ocultar menus sem permissao. | Usuario sem permissao nao ve modulo bloqueado. |
| AUTH-024 | P1 | Frontend | Criar tela de usuarios e perfis. | Gestor administra usuarios, perfis e status. |
| AUTH-025 | P1 | Frontend | Criar tela de permissoes em modo leitura no MVP. | Gestor visualiza permissoes de cada perfil. |
| AUTH-026 | P1 | QA | Criar testes de permissao por perfil. | Testes cobrem gestor, coordenador, lider e telefonista. |
| AUTH-027 | P1 | QA | Criar teste de isolamento entre tenants. | Usuario tenant A nao lista nem altera dados tenant B. |
| AUTH-028 | P2 | Backend | Implementar MFA opcional para gestores. | Gestor pode habilitar segundo fator. |
| AUTH-029 | P2 | Backend | Implementar politicas avancadas de expiracao de sessao. | Sessao expira por inatividade e data limite. |
| AUTH-030 | P2 | Frontend | Criar historico de acessos do usuario. | Gestor visualiza sessoes e acessos recentes. |

## Matriz inicial de permissoes

| Perfil | Acesso base |
| --- | --- |
| Gestor | Todos os modulos do tenant, configuracoes, usuarios, exportacoes e dashboards. |
| Coordenador territorial | Dados, metas, eventos e demandas dos territorios permitidos. |
| Lider | Pessoas, liderados, metas e eventos vinculados a propria lideranca. |
| Telefonista/atendimento | Consulta e cadastro de pessoas, contatos, demandas e interacoes permitidas. |
| Administrativo/RH | Agenda, tarefas operacionais, relatorios administrativos e cadastros internos permitidos. |

## Regras de seguranca

- Nenhum endpoint privado deve confiar no `tenant_id` enviado pelo cliente.
- O `tenant_id` deve vir do token/sessao e ser aplicado no banco.
- Exportacoes sempre exigem permissao explicita.
- Dados sensiveis devem ser mascarados para perfis operacionais quando aplicavel.
- Toda alteracao em pessoa, lideranca, meta, demanda, evento e permissao deve gerar auditoria.

## Entidades principais

- `auth.usuario`
- `auth.perfil_acesso`
- `auth.permissao`
- `auth.usuario_perfil`
- `auth.perfil_permissao`
- `auth.sessao_usuario`
- `auth.politica_acesso_territorial`
- `auditoria.log_auditoria`
- `auditoria.log_exportacao`

## Definition of Done

- Login, logout e `/auth/me` funcionam.
- RLS e tenant atual estao validados em teste.
- Permissoes bloqueiam acoes indevidas.
- Usuarios e perfis basicos sao administraveis.
- Auditoria cobre mutacoes sensiveis e exportacoes.
