# SPEC-17 - Aprimoramentos do Cadastro Pos-MVP

Status: backlog  
Prioridade principal: P2  
Modulo: `mod_cadastro`, `frontend_core/cadastro`, `backend_jobs_celery`  
Origem: revisao de aderencia da `SPEC-04-cadastro-pessoas-eleitores-liderancas.md`  
Objetivo: evoluir o cadastro operacional entregue no MVP, aumentando qualidade de dados,
rastreabilidade, capacidade de manutencao e experiencia de deteccao de duplicidades.

## Decisao de produto

As lacunas registradas nesta spec nao bloqueiam o MVP funcional porque:

- CPF e titulo eleitoral duplicados ja sao bloqueados por tenant.
- Telefone, e-mail e nome/data ja geram suspeitas por igualdade.
- Pessoas sem lider ja entram na fila de validacao.
- Cadastro, edicao, inativacao, hierarquia, segmentacao e merge assistido estao operacionais.
- As alteracoes principais de pessoa e o merge ja possuem auditoria.

A auditoria dos vinculos de tipos, tags e comunidades deve ser tratada primeiro nesta spec,
preferencialmente antes do uso com dados reais em producao, por envolver classificacoes
potencialmente sensiveis.

## Escopo

- Associacao assistida de endereco com municipio, bairro e UF.
- Deteccao de duplicidade por multiplos campos e similaridade.
- Reavaliacao de duplicidade apos alteracoes cadastrais.
- Detalhe consolidado com todos os vinculos e historico de auditoria.
- Manutencao de liderancas no frontend.
- Auditoria de todos os vinculos de segmentacao.
- Testes de integracao executados obrigatoriamente em PostgreSQL no CI.

## Fora do escopo

- Enriquecimento de endereco por bases comerciais externas.
- Geocodificacao massiva e mapas de calor.
- Merge totalmente automatico de pessoas.
- Score preditivo de engajamento ou propensao politica.
- Analise de redes sociais por servicos externos.

## Tarefas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| CAD17-001 | P2 | Backend | Resolver referencias territoriais do endereco. | Ao receber UF, municipio e bairro textuais, a API associa `municipio_id` e `bairro_id` quando houver correspondencia inequivoca e preserva o texto quando nao houver. |
| CAD17-002 | P2 | Backend | Validar consistencia entre bairro, municipio e UF. | A API rejeita combinacoes em que o bairro nao pertence ao municipio ou o municipio nao pertence a UF informada. |
| CAD17-003 | P2 | Frontend | Adicionar seletores territoriais ao formulario de endereco. | Usuario seleciona UF, municipio e bairro usando referencias globais, com alternativa de texto livre quando necessario. |
| CAD17-004 | P2 | Backend | Criar verificacao consolidada de duplicidade antes do cadastro. | Endpoint recebe nome, nascimento, documentos e contatos e devolve candidatos agrupados por criterio, sem criar pessoa. |
| CAD17-005 | P2 | Backend | Implementar similaridade de nome. | Nomes normalizados e data de nascimento geram suspeita conforme limiar documentado; acentos, caixa e espacos nao impedem comparacao. |
| CAD17-006 | P2 | Backend | Reavaliar duplicidades em alteracoes. | Inclusao ou edicao de CPF, titulo, telefone, e-mail, nome ou nascimento bloqueia duplicidade forte ou cria/atualiza suspeita fraca. |
| CAD17-007 | P2 | Backend | Tornar explicito o tratamento de CPF e titulo nas suspeitas. | Bloqueios fortes retornam candidato e criterio; quando houver excecao autorizada, a decisao e a suspeita ficam auditadas. |
| CAD17-008 | P2 | Frontend | Melhorar alerta de duplicidade no wizard. | Nome/data, todos os documentos e todos os contatos sao verificados juntos; mascaras sao normalizadas e cada candidato mostra os criterios encontrados. |
| CAD17-009 | P2 | Backend | Completar o contrato de detalhe da pessoa. | Resposta inclui relacionamentos de entrada e saida, validacoes, redes sociais, complemento politico e resumo da auditoria. |
| CAD17-010 | P2 | Frontend | Completar abas do detalhe da pessoa. | Usuario visualiza relacionamentos, redes sociais, complemento politico, validacoes e historico real de alteracoes. |
| CAD17-011 | P2 | Frontend | Permitir manutencao de liderancas. | Usuario autorizado cria e edita tipo, coordenador, apelido, meta e status da lideranca sem chamar a API manualmente. |
| CAD17-012 | P1 | Backend | Auditar tipos e vinculos de segmentacao. | Inclusao, substituicao ou remocao de tipos, tags e comunidades registra usuario, tenant, antes, depois, data e entidade afetada. |
| CAD17-013 | P1 | Backend | Auditar vinculos familiares e alteracoes de lideranca. | Inclusao, alteracao ou encerramento dos vinculos registra trilha com antes e depois. |
| CAD17-014 | P1 | QA/DevOps | Executar testes de integracao do cadastro no CI. | Pipeline provisiona PostgreSQL, aplica todas as migrations e executa CAD-047, CAD-048, CAD-049, CAD-051 e testes do job de completude sem `skip`. |
| CAD17-015 | P2 | QA | Criar testes de regressao das melhorias. | Testes cobrem endereco territorial, similaridade, duplicidade apos edicao, auditoria de vinculos e detalhe consolidado. |
| CAD17-016 | P2 | QA | Criar fluxo E2E do cadastro ampliado. | Teste cria pessoa, detecta candidato duplicado, atribui lider, segmenta, consulta historico e valida isolamento entre tenants. |

## Regras de negocio

- Referencias territoriais so podem ser preenchidas automaticamente quando a correspondencia for
  inequivoca.
- Texto original de endereco deve ser preservado para revisao e rastreabilidade.
- CPF e titulo eleitoral continuam sendo criterios fortes por tenant.
- Similaridade nunca deve mesclar registros automaticamente.
- Toda suspeita deve informar os criterios e valores normalizados que motivaram a decisao, sem
  expor dados para outro tenant.
- Alteracoes em classificacoes politicas, comunidades e liderancas devem sempre gerar auditoria.
- O historico apresentado no frontend deve respeitar permissoes e mascaramento de dados sensiveis.

## Dependencias

- Tabelas globais de UF, municipio e bairro populadas.
- Extensao `pg_trgm` disponivel para similaridade no PostgreSQL.
- Infraestrutura de auditoria da SPEC-03.
- Ambiente PostgreSQL efemero no pipeline de CI.

## Definition of Done

- Todos os criterios de aceite desta spec possuem teste automatizado.
- Testes de integracao executam sem `skip` no CI.
- Operacoes novas respeitam tenant e RLS.
- Alteracoes sensiveis geram auditoria com antes e depois.
- Frontend exibe erros e candidatos de duplicidade de forma acionavel.
- Contratos OpenAPI e tipos TypeScript permanecem sincronizados.
- Fluxo completo foi validado com dados representativos de pelo menos dois tenants.
