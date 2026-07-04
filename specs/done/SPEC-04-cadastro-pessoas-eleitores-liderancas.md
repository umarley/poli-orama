# SPEC-04 - Cadastro de Pessoas, Eleitores e Liderancas

Prioridade principal: P1  
Modulo: `mod_cadastro`, `frontend_core/cadastro`  
Objetivo: criar a base operacional do SaaS, permitindo cadastrar pessoas, eleitores, apoiadores, lideres, coordenadores, liderados, contatos, enderecos, tags, comunidades, nucleos familiares e vinculos de indicacao.

## Escopo MVP

- Cadastro completo de pessoa.
- Documentos, contatos, redes sociais e enderecos.
- Dados eleitorais.
- Tipos de pessoa.
- Liderancas e hierarquia de campo.
- Vinculo "quem indicou quem".
- Tags, comunidades e nucleos familiares.
- Busca e filtros operacionais.
- Deteccao e tratamento inicial de duplicidades.

## Fora do MVP

- Score avancado de engajamento.
- Merge automatico sofisticado de duplicidades.
- Grafo visual completo da rede de relacionamento.
- Enriquecimento automatico por bases externas.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| CAD-001 | P1 | Backend | Mapear entidades centrais de cadastro. | Models/schemas criados para pessoa, documentos, contatos, enderecos, eleitor e lideranca. |
| CAD-002 | P1 | Backend | Criar endpoint `GET /cadastro/pessoas` com paginacao e filtros. | Lista por nome, CPF, telefone, tipo, lider, territorio e tag. |
| CAD-003 | P1 | Backend | Criar endpoint `POST /cadastro/pessoas`. | Pessoa e criada com tenant atual e auditoria. |
| CAD-004 | P1 | Backend | Criar endpoint `GET /cadastro/pessoas/{id}`. | Retorna detalhe consolidado da pessoa. |
| CAD-005 | P1 | Backend | Criar endpoint `PATCH /cadastro/pessoas/{id}`. | Atualizacao parcial registra auditoria. |
| CAD-006 | P1 | Backend | Criar endpoint para inativar pessoa. | Pessoa sai das listagens padrao sem apagar historico. |
| CAD-007 | P1 | Backend | Implementar documentos pessoais. | CPF, RG, titulo eleitoral e outros documentos podem ser adicionados. |
| CAD-008 | P1 | Backend | Validar CPF quando informado. | CPF invalido gera erro de validacao. |
| CAD-009 | P1 | Backend | Validar unicidade forte de CPF por tenant. | Cadastro duplicado por CPF e bloqueado ou sinalizado conforme regra. |
| CAD-010 | P1 | Backend | Implementar contatos da pessoa. | Telefone, WhatsApp e e-mail podem ser salvos e marcados como principal. |
| CAD-011 | P1 | Backend | Validar formato de telefone e e-mail. | Dados invalidos retornam erro claro. |
| CAD-012 | P1 | Backend | Implementar redes sociais da pessoa. | Instagram, Facebook, TikTok, X e outros podem ser registrados. |
| CAD-013 | P1 | Backend | Implementar enderecos estruturados. | Endereco residencial, eleitoral, comercial ou temporario pode ser vinculado. |
| CAD-014 | P1 | Backend | Associar endereco a municipio, bairro e UF quando possivel. | Endereco usa tabelas globais quando existe correspondencia. |
| CAD-015 | P1 | Backend | Implementar dados eleitorais em `cadastro.eleitor`. | Titulo, zona, secao e local de votacao podem ser salvos. |
| CAD-016 | P1 | Backend | Validar duplicidade por titulo eleitoral. | Titulo repetido no tenant gera suspeita ou bloqueio conforme regra. |
| CAD-017 | P1 | Backend | Implementar tipos de pessoa. | Pessoa pode ser eleitor, apoiador, lider, coordenador, liderado, voluntario etc. |
| CAD-018 | P1 | Backend | Implementar cadastro de lideranca. | Pessoa pode ter papel operacional de lideranca com tipo, coordenador e meta inicial. |
| CAD-019 | P1 | Backend | Implementar hierarquia de lideranca. | Coordenador, lider, liderado e apoiador podem ser vinculados. |
| CAD-020 | P1 | Backend | Impedir ciclos na hierarquia. | API rejeita relacao onde uma pessoa vira ancestral de si mesma. |
| CAD-021 | P1 | Backend | Implementar indicacao. | Sistema registra quem indicou quem, origem e data. |
| CAD-022 | P1 | Backend | Implementar relacionamento entre pessoas. | Relacoes familiar, apoio politico, institucional e comunitaria podem ser registradas. |
| CAD-023 | P1 | Backend | Implementar nucleos familiares. | Nucleo pode ser criado e pessoas podem ser vinculadas. |
| CAD-024 | P1 | Backend | Permitir pessoa em mais de um nucleo familiar. | API aceita multiplos vinculos com observacao quando necessario. |
| CAD-025 | P1 | Backend | Implementar comunidades. | Comunidade possui nome, tipo, territorio e descricao. |
| CAD-026 | P1 | Backend | Vincular pessoa a comunidades. | Pessoa pode ter zero ou mais comunidades. |
| CAD-027 | P1 | Backend | Implementar tags. | Gestor cria tags como `META 30`, `META 100` e segmentos. |
| CAD-028 | P1 | Backend | Vincular pessoa a tags. | Pessoa pode ter zero ou mais tags e filtros funcionam. |
| CAD-029 | P1 | Backend | Implementar complemento politico. | Vinculo politico, partido, cargo, funcao, interesses e engajamento podem ser salvos. |
| CAD-030 | P1 | Backend | Criar regra de cadastro sem lider. | Pessoa sem lider entra em status de revisao ou atribuicao pendente. |
| CAD-031 | P1 | Backend | Implementar `validacao_cadastro`. | Pendencias, aprovacao e rejeicao ficam registradas. |
| CAD-032 | P1 | Backend | Implementar `suspeita_duplicidade`. | Suspeitas sao criadas por CPF, telefone, e-mail, titulo e nome/data. |
| CAD-033 | P1 | Backend | Criar endpoint para listar suspeitas de duplicidade. | Gestor/operador autorizado visualiza suspeitas por status. |
| CAD-034 | P1 | Backend | Criar endpoint para resolver suspeita de duplicidade. | Usuario marca como duplicado, falso positivo ou pendente. |
| CAD-035 | P1 | Backend | Criar busca rapida por nome, documento e telefone. | Resultado retorna dados minimos para atendimento e cadastro. |
| CAD-036 | P1 | Frontend | Criar tela de listagem de pessoas. | Tabela com busca, filtros, paginacao e acoes. |
| CAD-037 | P1 | Frontend | Criar formulario/wizard de cadastro de pessoa. | Usuario cadastra dados basicos, contatos, endereco, tipos e lider. |
| CAD-038 | P1 | Frontend | Criar alerta de possivel duplicidade durante cadastro. | Usuario ve registros candidatos antes de salvar ou ao salvar. |
| CAD-039 | P1 | Frontend | Criar tela de detalhe da pessoa com abas. | Abas para dados, contatos, enderecos, eleitor, vinculos, tags, comunidades e historico. |
| CAD-040 | P1 | Frontend | Criar edicao de documentos, contatos e enderecos. | Usuario autorizado edita dados sem sair do detalhe. |
| CAD-041 | P1 | Frontend | Criar tela de liderancas. | Lista lideres, coordenadores, metas e territorios vinculados. |
| CAD-042 | P1 | Frontend | Criar visualizacao simples da hierarquia. | Usuario ve coordenador, lideres e liderados em arvore/lista. |
| CAD-043 | P1 | Frontend | Criar tela de tags. | Gestor cria, edita, inativa e filtra tags. |
| CAD-044 | P1 | Frontend | Criar tela de comunidades. | Gestor cria e vincula pessoas a comunidades. |
| CAD-045 | P1 | Frontend | Criar tela de nucleos familiares. | Usuario cria nucleo e associa membros. |
| CAD-046 | P1 | Frontend | Criar fila de cadastros pendentes de validacao. | Gestor aprova, rejeita ou atribui lider. |
| CAD-047 | P1 | QA | Criar testes de cadastro completo. | Teste cria pessoa com documento, contato, endereco, tipo e eleitor. |
| CAD-048 | P1 | QA | Criar testes de duplicidade. | CPF, titulo, telefone, e-mail e nome/data geram comportamento esperado. |
| CAD-049 | P1 | QA | Criar testes de hierarquia. | Sistema impede ciclos e respeita tenant. |
| CAD-050 | P2 | Frontend | Criar grafo visual da rede de indicacao. | Usuario visualiza quem indicou quem em grafo filtravel. |
| CAD-051 | P2 | Backend | Criar merge assistido de duplicidades. | Gestor mescla registros com auditoria e preservacao de historico. |
| CAD-052 | P2 | Jobs | Criar recalculo de score de completude cadastral. | Job atualiza indicador de completude por pessoa. |

## Regras de negocio

- Uma pessoa pode ter mais de um tipo.
- Uma pessoa pode estar em mais de um nucleo familiar quando houver justificativa.
- Uma pessoa pode estar sem lider, mas deve entrar em fluxo de validacao/atribuicao.
- Duplicidade forte por CPF ou titulo deve ser bloqueada ou exigir confirmacao especial.
- Telefone, e-mail e nome/data devem gerar suspeita quando houver semelhanca relevante.
- Lideranca e eleitor sao extensoes de pessoa, nao cadastros isolados.

## Entidades principais

- `cadastro.pessoa`
- `cadastro.pessoa_documento`
- `cadastro.pessoa_contato`
- `cadastro.pessoa_rede_social`
- `cadastro.endereco`
- `cadastro.pessoa_endereco`
- `cadastro.pessoa_tipo`
- `cadastro.pessoa_pessoa_tipo`
- `cadastro.eleitor`
- `cadastro.lideranca`
- `cadastro.hierarquia_lideranca`
- `cadastro.indicacao`
- `cadastro.relacionamento_pessoa`
- `cadastro.nucleo_familiar`
- `cadastro.pessoa_nucleo_familiar`
- `cadastro.comunidade`
- `cadastro.pessoa_comunidade`
- `cadastro.tag`
- `cadastro.pessoa_tag`
- `cadastro.pessoa_complemento_politico`
- `cadastro.validacao_cadastro`
- `cadastro.suspeita_duplicidade`

## Definition of Done

- Cadastro completo funciona com validacoes.
- Busca rapida localiza pessoa por nome, documento e telefone.
- Liderancas e hierarquia podem ser mantidas.
- Tags, comunidades e nucleos familiares estao operacionais.
- Duplicidades sao detectadas e tratadas com fluxo minimo.
- Acoes sensiveis geram auditoria.
