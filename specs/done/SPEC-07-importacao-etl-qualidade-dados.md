# SPEC-07 - Importacao, ETL e Qualidade de Dados

Status: concluida em 2026-07-03 para o escopo MVP e deduplicacao fuzzy P2.
As tarefas ETL-033, ETL-034 e ETL-035 dependem de contratos/fontes externos e
foram detalhadas na SPEC-20 para execucao pos-MVP.

Prioridade principal: P1  
Modulo: `backend_jobs_celery`, `etl`, `mod_cadastro`  
Objetivo: permitir importacao inicial de bases historicas e planilhas, com validacao, staging, deduplicacao, logs e carga controlada para cadastro.

## Escopo MVP

- Upload de CSV/Excel de pessoas.
- Cadastro de fonte de dado.
- Registro de importacao.
- Staging de pessoas.
- Validacao de campos obrigatorios.
- Padronizacao basica de CPF, telefone, e-mail e endereco.
- Deteccao de duplicidades.
- Relatorio de erros e avisos.
- Carga aprovada para cadastro.

## Fora do MVP

- Integracao automatica com GESPED por API.
- Ingestao automatica TSE/IBGE.
- OCR de PDFs e imagens.
- Airflow completo.
- Deduplicacao fuzzy avancada com score complexo.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| ETL-001 | P1 | Backend | Mapear entidades de ETL. | Models/schemas para fonte, importacao, arquivo, linha, erro, staging, job e logs. |
| ETL-002 | P1 | Backend | Criar CRUD de `fonte_dado`. | Gestor registra fonte como GESPED, planilha, TSE, IBGE ou formulario. |
| ETL-003 | P1 | Backend | Criar endpoint para iniciar importacao. | Importacao recebe arquivo, fonte e parametros. |
| ETL-004 | P1 | Backend | Salvar arquivo de importacao em storage configurado. | Registro `importacao_arquivo` aponta para arquivo armazenado. |
| ETL-005 | P1 | Jobs | Criar job de leitura de CSV. | Linhas sao lidas e persistidas em `importacao_linha`. |
| ETL-006 | P1 | Jobs | Criar job de leitura de Excel. | Primeira aba ou aba escolhida e processada. |
| ETL-007 | P1 | Jobs | Criar mapeamento de colunas. | Usuario pode mapear colunas da planilha para campos do cadastro. |
| ETL-008 | P1 | Jobs | Criar normalizacao de CPF. | CPF fica apenas com digitos e validacao. |
| ETL-009 | P1 | Jobs | Criar normalizacao de telefone. | Telefones sao padronizados para formato interno. |
| ETL-010 | P1 | Jobs | Criar normalizacao de e-mail. | E-mail e salvo em lowercase e validado. |
| ETL-011 | P1 | Jobs | Criar normalizacao basica de endereco. | Campos de logradouro, bairro, cidade, UF e CEP sao separados quando possivel. |
| ETL-012 | P1 | Jobs | Criar validacao de campos obrigatorios. | Linhas invalidas geram erro com campo e motivo. |
| ETL-013 | P1 | Jobs | Persistir dados em `etl.staging_pessoa`. | Linhas validas entram no staging com status. |
| ETL-014 | P1 | Jobs | Criar regras basicas em `regra_deduplicacao`. | Regras por CPF, titulo, telefone, e-mail e nome/data ficam configuradas. |
| ETL-015 | P1 | Jobs | Criar resultado de deduplicacao. | `resultado_deduplicacao` registra candidatos e score/regra. |
| ETL-016 | P1 | Backend | Criar endpoint de resumo da importacao. | Retorna total, validas, invalidas, duplicadas, pendentes e carregadas. |
| ETL-017 | P1 | Backend | Criar endpoint para listar erros. | Usuario ve linha, campo, valor e motivo. |
| ETL-018 | P1 | Backend | Criar endpoint para aprovar carga. | Somente usuario autorizado promove dados validos para cadastro. |
| ETL-019 | P1 | Jobs | Criar job de carga para cadastro. | Pessoas, documentos, contatos e enderecos sao criados conforme mapeamento. |
| ETL-020 | P1 | Jobs | Associar registros importados a fonte. | Pessoa criada possui fonte/origem rastreavel. |
| ETL-021 | P1 | Backend | Criar endpoint para cancelar importacao. | Importacao pendente pode ser cancelada sem carga. |
| ETL-022 | P1 | Backend | Criar endpoint para baixar relatorio de erros CSV. | Usuario autorizado exporta erros sem dados desnecessarios. |
| ETL-023 | P1 | Frontend | Criar tela de importacoes. | Lista importacoes com status e resumo. |
| ETL-024 | P1 | Frontend | Criar fluxo de upload. | Usuario seleciona fonte, arquivo e parametros. |
| ETL-025 | P1 | Frontend | Criar tela de mapeamento de colunas. | Usuario associa colunas da planilha aos campos esperados. |
| ETL-026 | P1 | Frontend | Criar tela de validacao e erros. | Usuario ve erros, avisos e duplicidades antes de aprovar. |
| ETL-027 | P1 | Frontend | Criar acao de aprovar carga. | Usuario confirma e acompanha processamento. |
| ETL-028 | P1 | QA | Testar importacao CSV valida. | Planilha simples cria pessoas no cadastro. |
| ETL-029 | P1 | QA | Testar importacao Excel valida. | Arquivo `.xlsx` e processado. |
| ETL-030 | P1 | QA | Testar linha invalida. | Erros aparecem sem interromper importacao inteira. |
| ETL-031 | P1 | QA | Testar duplicidade por CPF. | Registro duplicado fica sinalizado. |
| ETL-032 | P2 | Jobs | Criar deduplicacao fuzzy por nome/data. | Similaridades geram suspeita com score. |
| ETL-033 | P2 | Jobs | Criar integracao automatica com GESPED se houver API/exportacao. | Job importa base conforme mecanismo aprovado. |
| ETL-034 | P2 | Jobs | Criar importacao de dados TSE/IBGE. | Bases populam tabelas globais/dw conforme layout. |
| ETL-035 | P3 | Jobs | Criar OCR/extracao de texto de PDFs e imagens. | Texto extraido fica em `arquivo.documento_extraido`. |

## Regras de negocio

- Nenhuma importacao deve gravar direto no cadastro sem staging e aprovacao.
- Toda importacao deve ter fonte, usuario, arquivo e tenant.
- Erros por linha nao devem interromper as demais linhas.
- Duplicidade deve ser visivel antes da carga definitiva.
- Importacao deve preservar rastreabilidade da origem.

## Entidades principais

- `etl.fonte_dado`
- `etl.importacao`
- `etl.importacao_arquivo`
- `etl.importacao_linha`
- `etl.erro_importacao`
- `etl.staging_pessoa`
- `etl.job_processamento`
- `etl.log_processamento`
- `etl.regra_deduplicacao`
- `etl.resultado_deduplicacao`
- `cadastro.pessoa`
- `arquivo.arquivo`

## Definition of Done

- Usuario importa CSV/Excel.
- Sistema valida, padroniza e sinaliza erros/duplicidades.
- Usuario aprova carga.
- Pessoas validas entram no cadastro com origem rastreavel.
- Logs e status permitem acompanhar falhas.

## Evidencias da implementacao

- Migration `010 - importacao_etl_qualidade_dados.sql` com isolamento por tenant,
  permissoes, fontes, regras de deduplicacao, staging e rastreabilidade.
- API FastAPI em `backend_core/src/app/mod_etl`, incluindo CRUD de fontes,
  upload, mapeamento, resumo, erros, duplicidades, aprovacao, cancelamento e CSV.
- Jobs Celery em `backend_jobs_celery/src/jobs/imports.py` e
  `backend_jobs_celery/src/jobs/import_rules.py`.
- Telas de lista, upload, mapeamento, validacao, duplicidades e aprovacao em
  `frontend_core/src/pages/etl`.
- Testes unitarios e integrados para CSV, XLSX, validacao por linha,
  duplicidade por CPF, carga aprovada e origem da pessoa.
