# SPEC-16 - Qualidade, Seguranca, LGPD e Deploy

Prioridade principal: P0/P1  
Modulo: transversal  
Objetivo: garantir que o SaaS seja testavel, seguro, observavel, aderente a LGPD e pronto para operacao em ambientes local, staging e producao.

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

## Checklist de go-live MVP

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

- CI e deploy estao funcionando.
- Fluxos criticos possuem testes.
- Seguranca e LGPD possuem controles minimos implementados.
- Observabilidade permite diagnosticar falhas.
- Backup/restore foi validado.
- Go-live tem checklist executavel.
