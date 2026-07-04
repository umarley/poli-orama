# SPEC-22 - Aprimoramentos de demandas e atendimentos pos-MVP

Status: backlog  
Prioridade principal: P2/P3  
Origem: pendencias DEM-021 e DEM-033 e melhorias nao bloqueantes da SPEC-09  
Modulos: `backend_core/mod_demandas`, `backend_jobs_celery`, `frontend_core/demandas`, `frontend_core/cadastro`

## Contexto

O MVP da SPEC-09 esta funcionalmente implementado. O usuario consegue registrar e
acompanhar demandas, atribuir responsavel e prazo, registrar atendimento, alterar
status, consultar movimentacoes, exportar dados e visualizar indicadores no
dashboard.

Esta spec concentra os aprimoramentos que nao bloqueiam o MVP: cadastro rapido de
solicitante, classificacao NLP real, filtros adicionais na interface, melhor
legibilidade do historico, administracao de responsaveis e ampliacao da cobertura
automatizada.

## Objetivo

Completar o fluxo operacional sem obrigar o usuario a sair da demanda para cadastrar
um solicitante, substituir a classificacao por palavras-chave por um pipeline NLP
versionado e explicavel e fechar as melhorias de experiencia e QA identificadas na
validacao da SPEC-09.

## Tarefas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| DEM-021A | P2 | Frontend | Adicionar acao `Cadastrar novo solicitante` no formulario de demanda. | Ao nao encontrar uma pessoa, o usuario abre um cadastro rapido sem perder os dados ja preenchidos da demanda. |
| DEM-021B | P2 | Frontend/Backend | Integrar cadastro rapido com o cadastro de pessoas. | Modal reutiliza as validacoes e o endpoint oficial de pessoas, exige os campos minimos e respeita tenant, permissoes e regras de duplicidade. |
| DEM-021C | P2 | Frontend | Selecionar automaticamente o solicitante criado. | Depois do cadastro, a pessoa aparece nas opcoes, fica selecionada em `pessoa_solicitante_id` e o usuario continua o envio da demanda. |
| DEM-021D | P2 | QA | Testar busca e cadastro rapido de solicitante. | Testes cobrem pessoa existente, pessoa nova, duplicidade, erro de validacao, cancelamento do modal e preservacao dos dados da demanda. |
| DEM-020A | P2 | Frontend | Expor filtros de origem, lider e periodo. | Tela envia origem, lider, data inicial e data final para `GET /demandas`, permite combinar e limpar filtros e usa os mesmos parametros na exportacao. |
| DEM-014A | P2 | Frontend | Criar gerenciamento de responsaveis de atendimento. | Usuario autorizado lista, cria, edita, desativa e reativa responsaveis dos tipos pessoa, usuario, setor e area. |
| DEM-017A | P2 | Backend/Frontend | Enriquecer o historico de movimentacoes. | API retorna nomes de status, responsaveis e resultados anteriores e novos; interface deixa de exibir apenas IDs. |
| DEM-032A | P2 | QA/Jobs | Testar o processador de alertas de prazo. | Testes cobrem vencendo, vencido, demanda concluida, prazo alterado, idempotencia, responsavel, tenant e reprocessamento. |
| DEM-033A | P3 | NLP/Jobs | Implementar classificador NLP de categoria e prioridade. | Descricao retorna categoria e prioridade sugeridas por um modelo ou servico NLP, sem depender exclusivamente de uma lista fixa de palavras-chave. |
| DEM-033B | P3 | Backend | Retornar score e confianca da classificacao. | Resposta informa score por sugestao, limiar aplicado e motivo para aceitar ou rejeitar a classificacao automatica. |
| DEM-033C | P3 | Database/Jobs | Versionar modelo e classificacoes. | Demanda registra nome e versao do modelo, data da inferencia, entrada normalizada, scores e se a sugestao foi aceita ou alterada pelo usuario. |
| DEM-033D | P3 | Backend/Jobs | Manter fallback deterministico. | Indisponibilidade, timeout ou baixa confianca do NLP usa regras locais ou deixa a classificacao pendente sem impedir o cadastro da demanda. |
| DEM-033E | P3 | QA | Criar suite de precisao e fallback. | Dataset versionado mede precisao minima por categoria e prioridade e testa acentos, textos curtos, ambiguidades, baixa confianca, timeout e indisponibilidade. |
| DEM-QA-001 | P2 | QA/DevOps | Executar o fluxo integrado com PostgreSQL real. | Pipeline configura `TEST_DATABASE_URL`, aplica migrations, executa os testes integrados de demandas e falha quando houver teste ignorado por banco ausente. |
| DEM-QA-002 | P2 | Frontend/QA | Restaurar o typecheck global do frontend. | `pnpm typecheck` passa, incluindo a incompatibilidade atual de `codigo_uf_ibge` em `TerritoriosPage.tsx`, sem afrouxar os tipos. |

## Regras de negocio

- Cadastro rapido deve usar o mesmo dominio e as mesmas validacoes do cadastro
  principal de pessoas.
- Fechar o modal de solicitante nao pode limpar o formulario da demanda.
- Pessoa criada em outro tenant nunca pode ser selecionada.
- Sugestao NLP nunca deve sobrescrever silenciosamente uma escolha manual.
- Score abaixo do limiar configurado deve ser apresentado como sugestao de baixa
  confianca ou descartado.
- Toda inferencia deve registrar algoritmo e versao para permitir auditoria e
  reprocessamento.
- Falha do servico NLP nao pode impedir o cadastro manual da demanda.
- Filtros visiveis e exportacao devem usar exatamente o mesmo estado.
- Alertas de prazo devem continuar idempotentes por tenant, demanda, tipo e data de
  referencia.

## Estado atual de referencia

- O formulario busca solicitante existente e informa categoria, origem, descricao,
  territorio, lideranca, prioridade e prazo.
- Ainda nao existe cadastro de nova pessoa dentro do fluxo da demanda.
- A classificacao atual sugere categoria e prioridade por regras fixas e
  palavras-chave.
- A API aceita filtros por origem, lider e periodo, mas a tela expoe apenas status,
  categoria, responsavel e territorio.
- O processador de alertas existe, mas nao possui teste automatizado especifico.
- A tabela de movimentacoes exibe IDs de status em vez de nomes.
- A API cria responsaveis, mas nao existe gerenciamento frontend.
- Testes backend que dependem de `TEST_DATABASE_URL` sao ignorados quando nao ha
  PostgreSQL de teste configurado.
- Testes, lint, Ruff e MyPy dos modulos de demandas/jobs passam.
- O typecheck global do frontend possui falha fora de demandas em
  `frontend_core/src/pages/territorios/TerritoriosPage.tsx`, relacionada a
  `codigo_uf_ibge`.

## Dependencias

- SPEC-04 concluida para reutilizacao do cadastro de pessoas.
- SPEC-09 concluida como base funcional do modulo.
- SPEC-15 para estrategia compartilhada de NLP/ML, observabilidade e governanca de
  modelos.
- Ambiente PostgreSQL descartavel no CI com migrations 001 a 016 aplicadas.

## Definition of Done

- Solicitante pode ser pesquisado ou cadastrado sem sair da demanda.
- Pessoa recem-criada fica selecionada e os dados anteriores do formulario sao
  preservados.
- Filtros de origem, lider e periodo funcionam na tela e na exportacao.
- Responsaveis podem ser administrados pela interface.
- Historico apresenta valores legiveis, sem depender de IDs.
- Alertas de prazo possuem cobertura automatizada e idempotencia validada.
- Classificador NLP retorna categoria, prioridade, score e versao, com fallback
  seguro.
- Testes de precisao e integracao passam no CI com PostgreSQL real.
- `pnpm lint`, `pnpm typecheck`, testes backend, frontend e jobs passam sem
  regressao.
