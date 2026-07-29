# Contexto de campanha e dados permanentes

## Regra central

A campanha eleitoral é o contexto histórico da operação eleitoral. Cadastros que
continuam úteis no gabinete não são duplicados nem passam a pertencer a uma
campanha.

Uma meta pertence diretamente a `eleicao.campanha_eleicao` por meio de
`meta.meta_voto.campanha_eleicao_id`. `meta.periodo_meta` serve somente para
subdivisão operacional e não define mais a eleição ou a campanha.

## Organização de lideranças

`cadastro.lideranca` continua representando a liderança permanente do tenant.
O papel exercido em cada campanha fica em:

- `eleicao.campanha_lideranca`: tipo, coordenador, apelido eleitoral e situação
  da liderança naquela campanha;
- `eleicao.campanha_liderado`: pessoa atribuída ao líder naquela campanha;
- índice único parcial em `(campanha_eleicao_id, pessoa_id) WHERE ativo = TRUE`.

Esse índice é a garantia de que uma pessoa gera no máximo um voto projetado na
mesma campanha. Em uma campanha futura ela pode ser atribuída a outra liderança,
sem alterar o histórico.

O possível voto e a base projetada são calculados a partir de
`eleicao.campanha_liderado`. A confirmação declarada continua vindo de
`eleicao.confirmacao_operacional_voto`, para a mesma campanha e pessoa. Nenhuma
dessas informações representa comprovação do voto depositado na urna.

## Metas e ranking

- `meta.meta_voto.campanha_eleicao_id` é obrigatório.
- Alvos e acompanhamentos herdam a campanha pela meta.
- `meta.ranking_lideranca` é único por campanha, liderança e data.
- O ranking usa apenas lideranças e liderados ativos na campanha.
- Eventos e demandas só pontuam no ranking eleitoral quando possuem o mesmo
  `campanha_eleicao_id`.

O backend de metas opera sobre a campanha ativa do tenant. Se não houver campanha
ativa, criação, consulta e recálculo de metas são recusados.

## Contexto político da pessoa

Informações mutáveis entre campanhas ficam em
`eleicao.pessoa_contexto_campanha`, com um registro por pessoa e campanha:

- nível de engajamento;
- situação de apoio;
- liderança atribuída;
- observações eleitorais.

Intenção e confirmação operacional de voto permanecem nas tabelas eleitorais
específicas. Dados permanentes não devem ser sobrescritos para representar uma
campanha.

## Associações opcionais

As entidades permanentes continuam independentes, mas podem ser selecionadas para
uso eleitoral por tabelas associativas:

- `eleicao.campanha_indicacao`;
- `eleicao.campanha_comunidade`;
- `eleicao.campanha_tag`.

Agenda, demandas, campanhas de comunicação e importações possuem
`campanha_eleicao_id` opcional:

- `agenda.evento.contexto`: `campanha`, `gabinete` ou `institucional`;
- `demanda.demanda.origem_contexto`: `campanha`, `gabinete` ou `institucional`;
- `comunicacao.campanha_comunicacao.campanha_eleicao_id`;
- `etl.importacao.campanha_eleicao_id`.

Eventos e demandas com contexto `campanha` exigem uma campanha. Registros de
gabinete ou institucionais podem permanecer sem esse vínculo.

## Dados vinculados à eleição, não à campanha

Bases estatísticas do TSE são compartilháveis e pertencem a
`eleicao.eleicao`. As tabelas `etl.staging_eleitorado_tse`,
`dw.perfil_eleitorado_tse` e `dw.perfil_eleitorado_secao_tse` recebem
`eleicao_id`; o ano permanece como atributo, mas deixa de ser a única forma de
distinguir eleições, turnos e eleições suplementares.

`eleicao.eleicao` é um catálogo oficial global da plataforma:

- não possui `tenant_id`;
- é consultável por todos os tenants;
- somente usuários com perfil `gestor_saas` podem criar ou alterar registros;
- campanhas dos tenants apenas selecionam uma eleição previamente cadastrada;
- eleições já vinculadas a campanhas não podem ser inativadas.

A manutenção é feita pela rota administrativa `/admin/eleicoes` e pelos
endpoints `/api/v1/eleicoes`. A estrutura global é consolidada pela migration
`030 - catalogo_global_eleicoes.sql`.

## Dados que permanecem globais ou permanentes

Não recebem vínculo direto com campanha:

- pessoas, documentos, contatos, endereços e redes sociais;
- título, zona, seção e local de votação da pessoa;
- estados, municípios, bairros, zonas, seções e locais de votação;
- religiões, profissões, escolaridades e partidos;
- núcleos familiares;
- comunidades e tags;
- consentimentos de comunicação;
- demandas e eventos institucionais;
- arquivos e auditoria, que herdam o contexto da entidade associada.

## Migração

A estrutura é criada por
`database/migrations/029 - contexto_historico_campanha.sql`.

A migração tenta inferir a campanha das metas existentes usando a eleição do
período e, quando existir apenas uma campanha no tenant, essa campanha única. Ela
interrompe a execução se alguma meta continuar ambígua, evitando atribuição
histórica incorreta. Rankings antigos sem campanha inferível são removidos porque
são projeções recalculáveis.

## Encerramento e consolidação analítica

Ao final da eleição, um usuário com `configuracoes.administrar` acessa
`/campanha/encerramento` e informa os votos oficiais, o total de votos válidos,
se o candidato foi eleito, a colocação e a fonte do resultado.

A API registra `eleicao.encerramento_campanha`, cria um
`etl.job_processamento` e retorna HTTP `202`. O processamento é executado pelo
worker Celery `jobs.campanhas.close`; a conexão HTTP não permanece aberta.

O worker usa uma trava transacional por campanha, recria o snapshot de forma
idempotente e grava:

- `dw.campanha_consolidada`: resultado oficial e indicadores gerais;
- `dw.lideranca_campanha_consolidada`: desempenho final das lideranças;
- `dw.meta_campanha_consolidada`: resultado final das metas;
- `dw.pessoa_campanha_consolidada`: ponte analítica pessoa–campanha, sem copiar
  nomes, contatos, documentos ou endereços.

Somente depois da consolidação terminar com sucesso a campanha recebe
`ativa = false` e `data_encerramento`. Em caso de erro, a campanha continua
ativa, a mensagem é registrada e o usuário pode solicitar reprocessamento.

Essa estrutura é criada pela migration
`031 - encerramento_campanha_dw.sql`.
