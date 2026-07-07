# SPEC-11 - Arquivos, Anexos e Data Lake

Prioridade principal: P2  
Modulo: `arquivo`, `backend_core`, `backend_jobs_celery`  
Objetivo: armazenar fotos, convites, pautas, documentos, planilhas e anexos com metadados, associacao a entidades e base para data lake.

## Escopo MVP reduzido

- Suporte minimo para foto de pessoa e arquivo de importacao.
- Registro logico em `arquivo.arquivo`.
- Associacao por `arquivo.anexo`.

## Escopo P2

- Upload generico de anexos.
- Storage configuravel local/S3/SeaweedFS.
- Anexos em pessoa, evento, demanda, comunicacao e importacao.
- Validacao de tamanho, extensao e hash.
- Extracao futura de texto.

## Fora do MVP

- OCR de imagem.
- Busca full-text em documentos extraidos.
- Antimalware corporativo completo.
- Versionamento sofisticado de documentos.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| ARQ-001 | P1 | Backend | Mapear entidades `tipo_anexo`, `arquivo`, `anexo`, `documento_extraido`. | Models/schemas criados. |
| ARQ-002 | P1 | Backend | Criar adapter de storage local para desenvolvimento. | Arquivo e salvo fora do banco e caminho fica persistido. |
| ARQ-003 | P1 | Backend | Criar upload de foto de pessoa. | Pessoa pode ter foto armazenada e referenciada. |
| ARQ-004 | P1 | Backend | Criar upload de arquivo de importacao. | Importacao recebe arquivo e metadados. |
| ARQ-005 | P1 | Backend | Validar extensao e tamanho maximo. | Arquivo invalido e rejeitado com erro claro. |
| ARQ-006 | P1 | Backend | Calcular hash do arquivo. | Hash fica salvo para rastreio e deduplicacao futura. |
| ARQ-007 | P1 | Frontend | Adicionar upload de foto no cadastro. | Usuario envia, remove ou troca foto conforme permissao. |
| ARQ-008 | P1 | QA | Testar upload de foto e importacao. | Arquivo fica acessivel apenas por usuario autorizado. |
| ARQ-009 | P2 | Backend | Criar CRUD de `tipo_anexo`. | Tipos como foto, convite, pauta, PDF, planilha e documento pessoal. |
| ARQ-010 | P2 | Backend | Criar endpoint de upload generico. | Upload recebe tipo e entidade alvo. |
| ARQ-011 | P2 | Backend | Criar endpoint para listar anexos de uma entidade. | Pessoa/evento/demanda mostram anexos vinculados. |
| ARQ-012 | P2 | Backend | Criar endpoint de download assinado/controlado. | Download exige permissao e nao expoe caminho interno. |
| ARQ-013 | P2 | Backend | Criar endpoint para remover/inativar anexo. | Remocao logica preserva auditoria. |
| ARQ-014 | P2 | Backend | Criar adapter S3 compativel. | Storage remoto funciona por configuracao. |
| ARQ-015 | P2 | Backend | Criar adapter SeaweedFS se escolhido. | Storage alternativo funciona por configuracao. |
| ARQ-016 | P2 | Frontend | Criar componente de anexos reutilizavel. | Pessoa, evento e demanda usam o mesmo componente. |
| ARQ-017 | P2 | Frontend | Criar preview seguro de imagem/PDF quando possivel. | Usuario ve metadados e preview sem baixar quando permitido. |
| ARQ-018 | P2 | Frontend | Criar anexos em evento. | Convite e pauta podem ser anexados. |
| ARQ-019 | P2 | Frontend | Criar anexos em demanda. | Comprovantes e documentos podem ser anexados. |
| ARQ-020 | P2 | QA | Testar permissao de download. | Usuario sem acesso nao baixa anexo. |
| ARQ-021 | P3 | Jobs | Criar extracao de texto de PDF. | Texto fica salvo em `documento_extraido`. |
| ARQ-022 | P3 | Jobs | Criar extracao OCR de imagem. | Texto extraido fica vinculado ao arquivo. |
| ARQ-023 | P3 | Backend | Criar busca por documentos extraidos. | Busca retorna arquivos conforme permissao. |

## Regras de negocio

- Arquivo nao deve ser salvo apenas no banco relacional.
- Banco deve guardar metadados, hash, tipo, tamanho, storage e chave/caminho.
- Download deve passar pelo backend ou URL assinada.
- Anexos herdam permissao da entidade vinculada.
- Upload de documento pessoal e dado sensivel e deve gerar auditoria.

## Entidades principais

- `arquivo.tipo_anexo`
- `arquivo.arquivo`
- `arquivo.anexo`
- `arquivo.documento_extraido`
- `cadastro.pessoa`
- `agenda.evento`
- `demanda.demanda`
- `etl.importacao`

## Definition of Done

- Fotos e arquivos de importacao funcionam no MVP.
- Anexos genericos ficam prontos na P2.
- Acesso e download respeitam tenant e permissao.
- Metadados permitem auditoria e migracao para data lake.
