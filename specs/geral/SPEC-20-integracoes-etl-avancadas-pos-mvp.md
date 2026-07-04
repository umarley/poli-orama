# SPEC-20 - Integracoes ETL avancadas pos-MVP

Status: backlog dependente de definicoes externas  
Prioridade principal: P2/P3  
Origem: tarefas ETL-033, ETL-034 e ETL-035 da SPEC-07  
Modulos: `backend_jobs_celery`, `backend_core`, `etl`, `dw`, `arquivo`

## Objetivo

Completar as integracoes externas e a extracao documental que nao podem ser
implementadas de forma verificavel sem contrato de API, layouts oficiais,
credenciais, politica de atualizacao e motor de OCR definidos.

O importador generico CSV/XLSX do MVP ja permite receber exportacoes manuais
identificadas pelas fontes GESPED, TSE e IBGE. Esta SPEC cobre a automacao e os
destinos especializados.

## Tarefas

| ID | Prioridade | Area | Tarefa | Dependencias | Criterio de aceite |
| --- | --- | --- | --- | --- | --- |
| ETL-033 | P2 | Jobs | Integrar automaticamente com GESPED. | Documentacao da API ou layout de exportacao aprovado, credenciais de homologacao, limites, paginacao e politica de consentimento. | Job incremental e idempotente autentica, pagina os dados, grava importacao/linhas/staging, respeita tenant, registra logs e permite aprovacao antes da carga. |
| ETL-034A | P2 | Jobs | Importar dados oficiais do TSE. | Dataset, ano eleitoral, URLs oficiais, dicionario e regra de atualizacao aprovados. | Download verificavel por hash, staging especializado, validacao de layout e carga idempotente em tabelas globais/DW, com metricas e rejeicoes. |
| ETL-034B | P2 | Jobs | Importar dados oficiais do IBGE. | APIs/datasets e versoes oficiais definidos, incluindo codigos territoriais de referencia. | Estados, municipios e demais recortes sao conciliados por codigo oficial sem duplicacao e com historico da fonte/versao. |
| ETL-035A | P3 | Arquitetura | Selecionar e homologar motor de OCR. | Decisao entre servico gerenciado e engine local, idiomas, custo, LGPD, retencao e limites. | ADR registra fornecedor/engine, ameacas, custo, precisao minima e estrategia de fallback. |
| ETL-035B | P3 | Jobs | Extrair texto de PDFs e imagens. | ETL-035A concluida e amostras representativas autorizadas. | Job valida MIME/tamanho, executa OCR em sandbox, persiste texto e metadados em `arquivo.documento_extraido`, registra confianca/falhas e evita reprocessamento pelo hash. |

## Regras obrigatorias

- Credenciais externas devem vir de secret manager e nunca do banco ou logs.
- Downloads oficiais devem registrar URL, data, versao e hash do artefato.
- Jobs devem ser idempotentes, reiniciaveis e observaveis.
- Dados de tenant nunca podem ser promovidos sem staging, validacao e aprovacao.
- OCR deve bloquear arquivos maliciosos, limitar CPU/memoria/tempo e respeitar
  a politica de retencao e descarte.
- Mudancas de layout devem falhar de forma explicita, sem carga parcial silenciosa.

## Definition of Ready

- Contratos, amostras e credenciais de homologacao disponiveis.
- Destino de cada campo aprovado pelo responsavel de dados.
- Frequencia, volume, SLA, retencao e responsavel operacional definidos.
- Casos de teste e dados anonimizados fornecidos.

## Definition of Done

- Integracoes executam em homologacao com dados reais autorizados.
- Testes de contrato detectam mudanca de layout/API.
- Reprocessamento nao duplica registros.
- Falhas e metricas aparecem em `etl.job_processamento` e
  `etl.log_processamento`.
- Runbook cobre credenciais, retry, indisponibilidade, recuperacao e auditoria.
