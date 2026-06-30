# SPEC-16 - Qualidade, Seguranca, LGPD e Deploy

Prioridade principal: P0/P1  
Modulo: transversal  
Objetivo: garantir que o SaaS seja testavel, seguro, observavel, aderente a LGPD e pronto para operacao em ambientes local, staging e producao.

## Ordem de execucao

Esta e a spec de fechamento do projeto. Sua execucao definitiva deve ocorrer
somente depois que as SPEC-01 a SPEC-15 previstas para o release estiverem
implementadas. Antes disso, seus itens podem orientar a arquitetura e o CI, mas
nao podem ser considerados concluidos apenas com modulos simulados, rotas
temporarias ou testes sem as entidades finais.

O inicio da SPEC-16 exige:

- migrations e modelos definitivos dos modulos anteriores;
- endpoints e fluxos frontend do release implementados;
- exportacoes, downloads e jobs do release identificados;
- classificacao dos dados pessoais e sensiveis coletados por cada modulo;
- matriz final de perfis, permissoes e escopos territoriais aprovada.

## Escopo MVP

- CI com lint, typecheck e testes.
- Testes backend, frontend e E2E dos fluxos criticos.
- Politicas basicas de LGPD e minimizacao.
- Mascaramento de dados sensiveis por perfil.
- Auditoria de acoes sensiveis.
- Controle de exportacao.
- Logs, metricas e health checks.
- Backup e restore documentados.
- Deploy staging/producao.

## Fora do MVP

- Certificacoes formais.
- SIEM completo.
- DLP corporativo.
- Pentest externo completo, embora recomendado antes de producao sensivel.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| QSD-001 | P0 | QA | Definir estrategia de testes por camada. | Documento descreve unitario, integracao, E2E e smoke. |
| QSD-002 | P0 | QA | Configurar cobertura minima backend. | Relatorio de cobertura e gerado no CI. |
| QSD-003 | P0 | QA | Configurar cobertura minima frontend. | Testes de componentes e fluxos rodam no CI. |
| QSD-004 | P0 | QA | Criar smoke test da API. | Health, login e `/auth/me` sao testados. |
| QSD-005 | P0 | QA | Criar smoke test do frontend. | Login e dashboard inicial abrem. |
| QSD-006 | P1 | QA | Criar E2E de cadastro de pessoa. | Fluxo cria pessoa com contato/endereco. |
| QSD-007 | P1 | QA | Criar E2E de lideranca e meta. | Fluxo cria lider e meta vinculada. |
| QSD-008 | P1 | QA | Criar E2E de importacao. | Planilha valida entra em staging e carga aprovada. |
| QSD-009 | P1 | QA | Criar E2E de demanda. | Demanda criada, atribuida e concluida. |
| QSD-010 | P1 | QA | Criar E2E de agenda. | Evento criado aparece no calendario. |
| QSD-011 | P0 | Seguranca | Definir matriz de dados sensiveis. | Campos como CPF, titulo, telefone e dados politicos possuem classificacao. |
| QSD-012 | P0 | Seguranca | Implementar mascaramento por perfil. | Perfis operacionais veem dados sensiveis mascarados quando aplicavel. |
| QSD-013 | P0 | Seguranca | Bloquear exportacao sem permissao. | Usuario sem permissao recebe 403. |
| QSD-014 | P0 | Seguranca | Registrar log de exportacao. | Exportacao salva usuario, filtros, finalidade e volume. |
| QSD-015 | P0 | Seguranca | Validar RLS em testes automatizados. | Teste prova isolamento entre tenants. |
| QSD-016 | P0 | Seguranca | Configurar headers de seguranca no backend. | Respostas incluem headers basicos conforme ambiente. |
| QSD-017 | P0 | Seguranca | Configurar politica de CORS restrita. | Apenas origens permitidas acessam API. |
| QSD-018 | P0 | Seguranca | Validar input em todos os endpoints publicos. | Payload invalido nao gera erro interno nem injecao. |
| QSD-019 | P1 | LGPD | Criar inventario de dados pessoais. | Documento lista campos, finalidade, base legal proposta e retencao. |
| QSD-020 | P1 | LGPD | Criar politica de consentimento de comunicacao. | Consentimento/opt-out ficam registrados e respeitados. |
| QSD-021 | P1 | LGPD | Criar fluxo de solicitacao LGPD. | Canal e procedimento para acesso/correcao/exclusao ficam documentados. |
| QSD-022 | P1 | LGPD | Criar regra de minimizacao em formularios. | Site publico e frontend nao coletam campos sem finalidade. |
| QSD-023 | P1 | LGPD | Criar retencao/logica de inativacao. | Dados podem ser inativados preservando auditoria quando necessario. |
| QSD-024 | P0 | Observabilidade | Padronizar logs estruturados. | Logs incluem request id, usuario quando houver e tenant quando houver. |
| QSD-025 | P0 | Observabilidade | Criar health checks de API, banco, Redis e worker. | Monitoramento consegue detectar falha por componente. |
| QSD-026 | P1 | Observabilidade | Criar metricas de API. | Latencia, status code e taxa de erro sao coletadas. |
| QSD-027 | P1 | Observabilidade | Criar metricas de jobs. | Tempo, falhas e filas pendentes sao monitorados. |
| QSD-028 | P1 | Observabilidade | Criar alertas basicos. | Falha de API, banco, worker ou fila gera alerta operacional. |
| QSD-029 | P0 | DevOps | Criar `.env.example` para todos os projetos. | Variaveis obrigatorias documentadas sem segredos. |
| QSD-030 | P0 | DevOps | Criar Dockerfiles para API, frontend, site e worker. | Imagens buildam localmente. |
| QSD-031 | P0 | DevOps | Criar compose de staging ou guia equivalente. | Ambiente staging sobe com configuracao documentada. |
| QSD-032 | P1 | DevOps | Criar pipeline de deploy para staging. | Merge em branch definida publica staging. |
| QSD-033 | P1 | DevOps | Criar pipeline de deploy para producao. | Deploy exige aprovacao manual ou regra acordada. |
| QSD-034 | P1 | DevOps | Configurar migracoes controladas. | Banco aplica migration com rollback/backup planejado. |
| QSD-035 | P1 | DevOps | Definir estrategia de backup. | Frequencia, retencao e destino estao documentados. |
| QSD-036 | P1 | DevOps | Testar restore em ambiente nao produtivo. | Restore documentado e validado. |
| QSD-037 | P1 | DevOps | Configurar HTTPS e dominios. | Site, app e API usam TLS em staging/producao. |
| QSD-038 | P1 | Produto | Criar checklist de go-live. | Criticos de seguranca, dados, acesso e suporte estao listados. |
| QSD-039 | P1 | Produto | Criar plano de treinamento. | Gestores, coordenadores, lideres e telefonistas tem roteiro de uso. |
| QSD-040 | P1 | Produto | Criar plano de suporte inicial. | Canal, SLA interno e responsaveis definidos. |
| QSD-041 | P2 | Seguranca | Realizar pentest externo. | Relatorio de achados e plano de correcao. |
| QSD-042 | P2 | Observabilidade | Criar dashboard tecnico. | API, banco, jobs e filas aparecem em painel. |
| QSD-043 | P2 | DevOps | Criar ambiente de homologacao com dados mascarados. | Usuarios testam fluxos sem dados sensiveis reais. |
| QSD-044 | P0 | Arquitetura/QA | Inventariar todos os endpoints e tabelas com escopo de tenant. | Documento relaciona rota, tabela, permissao, regra RLS e spec de origem sem lacunas. |
| QSD-045 | P0 | Backend | Aplicar RBAC final em todos os endpoints privados. | Cada rota privada exige permissao explicita ou possui justificativa documentada para depender apenas de autenticacao. |
| QSD-046 | P0 | Backend/QA | Validar que APIs nao confiam em `tenant_id` recebido do cliente. | Criacoes e consultas usam o tenant do token/sessao; payload ou query string nao permitem trocar o tenant. |
| QSD-047 | P0 | Database | Revisar e completar RLS das tabelas tenant-aware criadas pelas SPEC-04 a SPEC-15. | Todas as tabelas com `tenant_id` possuem politica adequada e a role da aplicacao nao consegue contorna-la. |
| QSD-048 | P0 | QA | Criar matriz de testes de isolamento por modulo. | Cadastro, territorio, metas, ETL, agenda, demandas, relatorios, arquivos, comunicacao e modo eleicao provam leitura e mutacao isoladas entre tenants. |
| QSD-049 | P0 | Backend | Aplicar acesso territorial aos modulos dependentes. | Cadastro, metas, agenda, demandas, dashboards e exportacoes respeitam o filtro territorial reutilizavel da SPEC-05. |
| QSD-050 | P0 | QA | Testar acesso territorial por perfil e modulo. | Coordenador e lider nao listam, detalham, alteram nem exportam registros fora do escopo permitido. |
| QSD-051 | P0 | Backend | Completar auditoria de mutacoes dos dominios. | Criacao, edicao, inativacao e exclusao de pessoa, lideranca, meta, demanda, evento e configuracao de permissao registram antes/depois, ator, tenant e entidade. |
| QSD-052 | P0 | Backend | Auditar acessos sensiveis e downloads controlados. | Consulta ou download definido como sensivel registra ator, tenant, finalidade/alvo, data e resultado sem gravar o dado sensivel no log. |
| QSD-053 | P0 | Backend | Integrar auditoria em todas as exportacoes reais. | Exportacoes de cadastro, ETL, agenda, demandas, dashboards, relatorios e arquivos usam o helper comum de `log_exportacao`. |
| QSD-054 | P0 | QA | Testar autorizacao e auditoria das exportacoes. | Sem permissao a API retorna 403; com permissao e finalidade valida gera arquivo e log com filtros e volume. |
| QSD-055 | P0 | Backend/Frontend | Aplicar mascaramento conforme a matriz final de dados sensiveis. | APIs, telas, buscas, dashboards, exportacoes e logs ocultam CPF, titulo, telefone e dados politicos para perfis sem necessidade funcional. |
| QSD-056 | P1 | Backend/QA | Validar o vinculo entre usuario e pessoa da SPEC-04. | `auth.usuario.pessoa_id`, quando preenchido, referencia pessoa do mesmo tenant e nao permite associacao cruzada. |
| QSD-057 | P0 | Backend/Database | Reconciliar catalogo e seeds RBAC com todos os modulos entregues. | Toda acao protegida possui permissao cadastrada e os perfis basicos recebem exatamente a matriz final aprovada. |
| QSD-058 | P0 | QA | Testar a matriz RBAC final usando seeds e endpoints reais. | Gestor, coordenador, lider, telefonista e administrativo possuem testes positivos e negativos nos modulos aplicaveis. |
| QSD-059 | P1 | Frontend/QA | Reconciliar menus, rotas e acoes com a autorizacao final. | Item oculto nao e acessivel por URL e toda acao exibida corresponde a uma permissao que o backend tambem valida. |
| QSD-060 | P0 | Seguranca/QA | Validar integridade e acesso aos logs de auditoria. | Usuario comum nao altera/apaga logs, consultas sao restritas e tentativas indevidas sao bloqueadas. |
| QSD-061 | P0 | QA/Arquitetura | Produzir matriz final de rastreabilidade da SPEC-03. | AUTH-001 a AUTH-030 e regras transversais apontam implementacao, testes e evidencias; nenhuma pendencia fica classificada apenas como dependencia futura. |

## Fechamento das dependencias da SPEC-03

As tarefas abaixo nao representam nova implementacao isolada do modulo de
autenticacao. Elas validam e completam garantias da SPEC-03 que so podem ser
comprovadas quando os dominios consumidores existirem.

| Garantia da SPEC-03 | Specs das quais depende | Fechamento na SPEC-16 |
| --- | --- | --- |
| RLS e isolamento em dados operacionais (`AUTH-007`, `AUTH-008`, `AUTH-027`) | SPEC-04 a SPEC-15, conforme os modulos incluidos no release | QSD-044, QSD-046, QSD-047 e QSD-048 |
| RBAC aplicado a operacoes reais (`AUTH-009`, `AUTH-010`, `AUTH-023`, `AUTH-026`) | SPEC-04 a SPEC-15 | QSD-045, QSD-057, QSD-058 e QSD-059 |
| Escopo territorial efetivo (`AUTH-018` e `AUTH-019`) | SPEC-04, SPEC-05, SPEC-06, SPEC-08, SPEC-09 e SPEC-10 | QSD-049 e QSD-050 |
| Auditoria das mutacoes sensiveis (`AUTH-015` e `AUTH-016`) | SPEC-04, SPEC-06, SPEC-08, SPEC-09, SPEC-13 e SPEC-14 | QSD-051, QSD-052 e QSD-060 |
| Auditoria e autorizacao de exportacoes (`AUTH-017`) | SPEC-07, SPEC-08, SPEC-09, SPEC-10 e SPEC-11 | QSD-013, QSD-014, QSD-053 e QSD-054 |
| Mascaramento de dados por perfil | SPEC-04, SPEC-05, SPEC-10, SPEC-13, SPEC-14 e SPEC-15 | QSD-011, QSD-012 e QSD-055 |
| Vinculo opcional entre identidade e cadastro | SPEC-04 | QSD-056 |

Uma dependencia so pode ser marcada como resolvida quando houver teste contra a
implementacao real. Existencia de helper, model, migration ou teste com dados
artificiais isolados nao substitui a validacao no endpoint e no fluxo consumidor.

## Checklist de go-live MVP

- SPEC-01 a SPEC-15 previstas para o release concluidas e integradas.
- Matriz de rastreabilidade da SPEC-03 sem dependencias futuras.
- API, frontend, site e worker publicados.
- Banco aplicado e backup configurado.
- Tenant inicial criado.
- Usuarios e perfis criados.
- RLS validado.
- Importacao testada com planilha real ou amostra representativa.
- Cadastro, lideranca, meta, agenda, demanda e dashboard testados.
- Exportacao auditada.
- Paginas legais publicadas no site publico.
- Logs e alertas basicos ativos.
- Plano de suporte e treinamento executado.

## Regras transversais

- Dados sensiveis devem ser tratados como regra de produto, nao detalhe tecnico.
- Qualquer exportacao deve exigir finalidade.
- Auditoria deve ser imutavel para usuarios comuns.
- Segredos devem ficar fora do repositorio.
- Testes de tenant/RLS sao obrigatorios antes de producao.
- Staging deve evitar indexacao publica do site.

## Definition of Done

- QSD-044 a QSD-061 foram executadas contra os modulos reais do release.
- Nenhuma garantia de seguranca foi aceita apenas por existir na camada de infraestrutura.
- CI e deploy estao funcionando.
- Fluxos criticos possuem testes.
- Seguranca e LGPD possuem controles minimos implementados.
- Observabilidade permite diagnosticar falhas.
- Backup/restore foi validado.
- Go-live tem checklist executavel.
