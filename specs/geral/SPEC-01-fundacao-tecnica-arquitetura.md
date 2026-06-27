# SPEC-01 - Fundacao Tecnica e Arquitetura

Prioridade principal: P0  
Modulo: `backend_core`, `frontend_core`, `backend_jobs_celery`, `database`  
Objetivo: criar a base tecnica para desenvolvimento do SaaS em monolito modular, com separacao por dominios e estrutura pronta para multitenancy, API, frontend autenticado, jobs e qualidade.

## Escopo MVP

- Criar estrutura inicial do backend FastAPI.
- Criar estrutura inicial do frontend React + Vite.
- Criar estrutura inicial de jobs Celery/Redis.
- Integrar configuracao do banco existente.
- Definir padroes de API, erros, paginacao, autenticacao e modulos.
- Preparar Docker local, CI, lint, formatacao e testes.

## Fora do MVP

- Migracao para schemas por tenant.
- Microservicos independentes.
- Orquestracao Kubernetes.
- Observabilidade distribuida avancada.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| FND-001 | P0 | Backend | Criar projeto FastAPI em `backend_core` com estrutura `src/app`. | `GET /health` responde status da API. |
| FND-002 | P0 | Backend | Criar modulos base `core`, `tenants`, `mod_cadastro`, `mod_territorio`, `mod_metas`, `mod_agenda`, `mod_demandas`, `mod_dashboard`. | Pastas existem com `router`, `schemas`, `service` e `repository` quando aplicavel. |
| FND-003 | P0 | Backend | Configurar settings por ambiente usando variaveis de ambiente. | `.env.example` documenta variaveis sem segredos reais. |
| FND-004 | P0 | Backend | Configurar conexao assicrona com PostgreSQL. | Endpoint interno de health valida conexao opcional com banco. |
| FND-005 | P0 | Backend | Definir padrao de resposta para erros de validacao, regra de negocio e erro interno. | Erros retornam codigo HTTP, `code`, `message` e `details`. |
| FND-006 | P0 | Backend | Definir utilitario de paginacao, ordenacao e filtros simples. | Endpoints de listagem conseguem retornar `items`, `total`, `page`, `page_size`. |
| FND-007 | P0 | Backend | Configurar CORS para frontend local, staging e producao. | Frontend local consegue chamar API sem erro de CORS. |
| FND-008 | P0 | Backend | Configurar OpenAPI por tags de dominio. | Swagger agrupa endpoints por modulo. |
| FND-009 | P0 | Backend | Criar middlewares de request id e logging basico. | Cada request tem identificador nos logs. |
| FND-010 | P0 | Backend | Criar padrao de repository/service para acesso ao banco. | Primeiro modulo implementado segue o padrao. |
| FND-011 | P0 | Database | Documentar como aplicar a migration existente em ambiente local. | README ou spec tecnica descreve comando e variaveis. |
| FND-012 | P0 | Database | Validar schemas existentes do banco contra a migration. | Comando de validacao lista schemas/tabelas esperadas. |
| FND-013 | P0 | Frontend | Criar projeto React + Vite em `frontend_core`. | `npm run dev` abre tela base. |
| FND-014 | P0 | Frontend | Configurar TypeScript, ESLint, Prettier e aliases de importacao. | `npm run lint` roda sem erro no projeto inicial. |
| FND-015 | P0 | Frontend | Criar shell autenticado com layout, sidebar, header e area de conteudo. | Tela base renderiza navegacao principal. |
| FND-016 | P0 | Frontend | Configurar roteamento por modulos. | Rotas placeholder existem para dashboard, cadastro, liderancas, metas, agenda, demandas e configuracoes. |
| FND-017 | P0 | Frontend | Criar cliente HTTP com interceptador de token e tratamento de erro. | Chamadas exibem erro padronizado quando API falha. |
| FND-018 | P0 | Frontend | Configurar gerenciamento de estado leve com Zustand. | Store de sessao guarda usuario atual e tenant atual. |
| FND-019 | P0 | Frontend | Configurar TanStack Query ou equivalente para cache de chamadas. | Listagem placeholder usa query com loading, erro e sucesso. |
| FND-020 | P0 | Frontend | Criar componentes base de formulario, tabela, filtros, modal e toast. | Componentes sao reutilizados em pelo menos uma tela placeholder. |
| FND-021 | P0 | Frontend | Criar padrao responsivo para uso desktop e mobile basico. | Shell nao quebra em 1366px e 390px. |
| FND-022 | P0 | Jobs | Criar projeto `backend_jobs_celery` com worker Celery. | Worker sobe localmente e executa job de teste. |
| FND-023 | P0 | Jobs | Configurar Redis como broker local. | Job de teste entra na fila e conclui. |
| FND-024 | P0 | Jobs | Criar padrao de job com status e log em tabelas `etl.job_processamento` e `etl.log_processamento`. | Job de teste registra inicio, sucesso e erro simulado. |
| FND-025 | P0 | DevOps | Criar Docker Compose local para API, frontend, worker, Redis e Postgres opcional. | Ambiente local sobe com um comando documentado. |
| FND-026 | P0 | DevOps | Criar comandos padrao de desenvolvimento. | README lista comandos para instalar, rodar, testar e formatar. |
| FND-027 | P0 | QA | Configurar teste unitario no backend. | Pipeline roda ao menos um teste de health. |
| FND-028 | P0 | QA | Configurar teste unitario no frontend. | Pipeline roda ao menos um teste de renderizacao basica. |
| FND-029 | P1 | QA | Configurar teste E2E minimo com Playwright ou equivalente. | Teste abre login e valida shell. |
| FND-030 | P1 | DevOps | Criar CI para lint, typecheck e testes. | Pull request falha se lint ou teste falhar. |

## Decisoes tecnicas

- Manter nomes de dominio em portugues para alinhar com banco e negocio.
- Separar modulos por dominio, sem microservicos no MVP.
- Isolar regras de negocio em services, evitando regras pesadas dentro das rotas.
- Evitar acesso direto do frontend ao banco.
- Usar jobs para importacao, deduplicacao, geocodificacao e calculos pesados.

## Dependencias

- Banco existente aplicado em ambiente local.
- Variaveis de ambiente definidas para API e frontend.
- Decisao sobre gerenciador de pacotes Python e Node.

## Definition of Done

- Backend, frontend e worker sobem localmente.
- Health checks funcionam.
- Padroes de modulo estao documentados.
- Testes minimos rodam em CI.
- Nenhum segredo real esta versionado.
