# Regras do atendimento

## Objetivo

O atendimento operacional em `/comunicacao/atendimento` permite que o telefonista
assumir pessoas da campanha, registrar o contato, atualizar o cadastro enquanto o
atendimento estiver aberto e encerrar com uma situação. Cada tentativa gera um
registro em `comunicacao.atendimento_eleitor`.

A tela com `?janela=1` mostra a fila de atendimentos abertos do telefonista
autenticado e o detalhe do atendimento selecionado.

A contabilização de votos confirmados a partir do atendimento está em
[regras-metas-votos-e-confirmacoes.md](regras-metas-votos-e-confirmacoes.md).

## Papéis

| Perfil | Pode |
|---|---|
| `telefonista` | Assumir, cadastrar atendimento manual, buscar e retomar sem resposta/interrompido, operar, encerrar e invalidar atendimentos da própria fila |
| `gestor` | Consultar atendimento e indicadores; não assume pessoa na fila |

Somente o telefonista dono do atendimento edita cadastro, contatos, documentos e
encerramento. Depois de encerrado, a edição cadastral pelo atendimento é bloqueada.

## Fontes

| Informação | Fonte |
|---|---|
| Atendimento | `comunicacao.atendimento_eleitor` |
| Pessoa | `cadastro.pessoa` |
| Contatos | `cadastro.pessoa_contato` |
| Interações | `comunicacao.interacao` |
| Canal | catálogo de canais do tenant |
| Campanha | `eleicao.campanha_eleicao` (header `X-Campaign-ID` ou campanha ativa) |
| Confirmação de voto | `eleicao.confirmacao_operacional_voto` |
| Limite simultâneo | `tenant_configuracao.preferencias.maximo_atendimentos_simultaneos` |

## Fila de atendimentos abertos

A aba **Atendimentos abertos** lista somente registros do telefonista logado com
`situacao = 'em_atendimento'` e `finalizado_em` nulo.

Um atendimento encerrado **não reaparece** nessa lista. Se a pessoa voltar ao
sorteio, entra um **novo** atendimento.

### Limite simultâneo

O telefonista pode ter vários atendimentos abertos. O teto vem de
`maximo_atendimentos_simultaneos` (padrão 10, mínimo 1, máximo 50). Ao atingir o
limite, é preciso encerrar um atendimento antes de assumir outro.

Uma pessoa não pode ter dois atendimentos abertos ao mesmo tempo
(`uq_atendimento_eleitor_pessoa_ativo`).

### Assumir atendimento

`POST /api/v1/comunicacao/atendimento/iniciar` sorteia uma pessoa elegível no
tenant, cria o atendimento com `situacao = 'em_atendimento'` e preenche
`ultima_visualizacao_em` com o instante da criação.

A pessoa precisa estar ativa (`cadastro.pessoa.ativo` e `excluido_em` nulo) e não
ter atendimento aberto.

### Atendimento manual

`POST /api/v1/comunicacao/atendimento/manual` cadastra uma pessoa nova e já abre
o atendimento na mesma tela operacional. Campos:

| Campo | Obrigatório |
|---|---|
| Nome completo | Sim |
| Telefone (DDD + número) | Sim |
| E-mail | Não |
| Data de nascimento | Não |
| Sexo | Não |

O telefone é gravado em `cadastro.pessoa_contato` (`celular` com 11 dígitos ou
`telefone` com 10). O e-mail, se informado, vira contato `email`. A origem do
cadastro é `call_center`.

Antes de criar, o sistema bloqueia quando:

- o telefone já existe no tenant (com ou sem DDI 55), em `telefone`, `celular`
  ou `whatsapp`;
- a pessoa desse telefone já está `em_atendimento` com outro telefonista;
- a pessoa desse telefone já está na fila do próprio telefonista;
- o limite de atendimentos simultâneos foi atingido.

Se o cadastro for aceito, a pessoa entra imediatamente em `em_atendimento` com o
telefonista autenticado.

## Busca e retomada

Quando o atendimento é encerrado como `sem_resposta` (ou `interrompido`) e o
eleitor responde depois, o telefonista pode recuperar o **mesmo** registro na
tela operacional.

A seção **Buscar atendimento anterior** fica entre os botões de ação e as abas.
Informe nome (mínimo 2 letras) e/ou telefone (mínimo 8 dígitos). A busca
`GET /api/v1/comunicacao/atendimento/buscar` lista até 20 atendimentos da
campanha atual, priorizando `sem_resposta` e `interrompido`.

`POST /api/v1/comunicacao/atendimento/{id}/retomar` reabre o atendimento:

- volta `situacao` para `em_atendimento`, limpa `finalizado_em` e `resultado`;
- atribui o registro ao telefonista autenticado;
- grava a interação "Reabertura de atendimento";
- devolve o atendimento hidratado para a tela operacional.

### Pode retomar

| Situação | Efeito |
|---|---|
| `sem_resposta` | Reabre o mesmo atendimento |
| `interrompido` | Reabre o mesmo atendimento |
| `em_atendimento` do próprio telefonista | Só abre o registro já da fila |

### Não retoma

| Condição | Efeito |
|---|---|
| `concluido` ou `numero_invalido` | Encerramento definitivo |
| Pessoa com outro atendimento `concluido`/`numero_invalido` | Pessoa já saiu do fluxo operacional |
| Pessoa já `em_atendimento` | Não pode haver dois abertos |
| Cadastro inativo ou excluído | Fora do fluxo |
| Limite simultâneo atingido | Precisa encerrar outro da fila antes |

A retomada **não** cria um atendimento novo. O sorteio continua criando um
registro novo quando a pessoa volta à fila.

## Retorno à fila (sorteio)

O sorteio **não reabre** o atendimento antigo. Ele decide se a **pessoa** pode
receber um novo atendimento.

Quem já teve qualquer atendimento com `concluido` ou `numero_invalido` não é
sorteado de novo, mesmo que depois tenha havido `sem_resposta` ou `interrompido`.

### Não volta à fila

| Situação / condição | Efeito |
|---|---|
| `em_atendimento` | Pessoa ainda está com o telefonista |
| `concluido` | Tentativa encerrada; pessoa sai do sorteio |
| `numero_invalido` (Encerrar) | Tentativa encerrada; pessoa sai do sorteio sem inativar o cadastro |
| `numero_invalido` (Invalidar contato) | Encerra o atendimento, marca `pessoa.ativo = false` e preenche `excluido_em` |
| Pessoa inativa ou excluída | Fora do sorteio, independentemente da situação |

### Volta à fila

| Situação | Efeito |
|---|---|
| `sem_resposta` | Atendimento antigo permanece encerrado; a pessoa pode ser sorteada de novo |
| `interrompido` | Idem: novo atendimento, não o mesmo registro |

Pessoas nunca atendidas e ativas também entram no sorteio.

## Situações e resultados no encerramento

O encerramento (`POST /atendimento/{id}/encerrar`) grava `situacao`, `resultado`,
`finalizado_em` e uma interação automática. Intenção `nao_votara` exige motivo de
rejeição. `interrompido` e `numero_invalido` exigem motivo de encerramento.

| Situação | Resultado gravado | Volta ao sorteio |
|---|---|---|
| `concluido` + intenção `votara` | `confirmado` | Não |
| `concluido` + intenção `indeciso` | `indeciso` | Não |
| `concluido` + outras intenções | `concluido` | Não |
| Qualquer situação + intenção `nao_votara` | `nao_apoia` | Depende da situação, não da intenção |
| `sem_resposta` | `tentativa_sem_resposta` | Sim |
| `numero_invalido` | `numero_invalido` | Não |
| `interrompido` | `interrompido` | Sim |

Invalidar contato (`POST /atendimento/{id}/invalidar`) é ação distinta do
encerramento: situação `numero_invalido`, resultado `contato_invalido` e cadastro
inativado.

## Intenção de voto e confirmação

Intenções possíveis: `votara`, `nao_votara`, `indeciso`, `nao_respondeu`.

- `votara` cria ou reativa a confirmação operacional, somente se a pessoa tiver
  liderança ativa na campanha.
- `nao_votara` ou outra intenção posterior revoga uma confirmação ainda ativa.
- `sem_resposta`, `interrompido` e `numero_invalido` não apagam, por si sós, uma
  declaração já registrada; a revogação ocorre quando a intenção gravada deixa de
  ser `votara`.

Detalhes da meta e da unicidade da confirmação:
[regras-metas-votos-e-confirmacoes.md](regras-metas-votos-e-confirmacoes.md).

## Mensagens na fila aberta

A linha **Última mensagem** da aba Atendimentos abertos **não** usa
`ultima_visualizacao_em`.

| Dado na tela | Origem |
|---|---|
| Texto e horário da última mensagem | Última `comunicacao.interacao` da pessoa (`data_interacao`, `conteudo`) |
| Tempo relativo (`6 min`) | `ultima_interacao_em` ou, se não houver interação, `iniciado_em` |
| Mensagens não lidas | Interações de entrada com `data_interacao` posterior a `ultima_visualizacao_em` (ou a `iniciado_em`, se a visualização for nula) |

`ultima_visualizacao_em` é atualizado quando o telefonista dono abre o atendimento
ainda em andamento.

## Edição durante o atendimento

Enquanto `situacao = 'em_atendimento'` e `finalizado_em` for nulo, o telefonista
dono pode alterar dados da pessoa, documentos, contatos, canal, observação e
intenção. Após o encerramento, essas alterações pelo fluxo de atendimento são
recusadas.

## Indicadores

`GET /api/v1/comunicacao/indicadores` é exclusivo do gestor. Conta atendimentos da
campanha por situação, intenção, canal, telefonista e tempo médio. Não altera a
fila.

O nome do telefonista nos indicadores abre o relatório analítico
`/comunicacao/indicadores/atendente/{id}`. A lista
`GET /api/v1/comunicacao/indicadores/atendimentos` devolve os atendimentos
encerrados daquele atendente, com eleitor, horários, canal, intenção, observação
e motivos. Acima da lista, cards somam o recorte filtrado: total, concluído,
número inválido, sem resposta, interrompido, votará, não votará, indeciso e não
respondeu. Filtros: data inicial, data final e outro telefonista.

O motivo em **Principais motivos de rejeição** abre
`/comunicacao/indicadores/motivo/{id}` (`0` = sem motivo). A lista
`GET /api/v1/comunicacao/indicadores/rejeicoes` devolve os atendimentos com
intenção `nao_votara` daquele motivo, no mesmo formato analítico.

## APIs

Isoladas por tenant:

- `GET /api/v1/comunicacao/atendimento/abertos`
- `POST /api/v1/comunicacao/atendimento/iniciar`
- `POST /api/v1/comunicacao/atendimento/manual`
- `GET /api/v1/comunicacao/atendimento/buscar`
- `POST /api/v1/comunicacao/atendimento/{id}/retomar`
- `GET /api/v1/comunicacao/atendimento/{id}`
- `PATCH /api/v1/comunicacao/atendimento/{id}`
- `POST /api/v1/comunicacao/atendimento/{id}/encerrar`
- `POST /api/v1/comunicacao/atendimento/{id}/invalidar`
- `GET /api/v1/comunicacao/indicadores`
- `GET /api/v1/comunicacao/indicadores/atendimentos`
- `GET /api/v1/comunicacao/indicadores/rejeicoes`

## Auditoria e privacidade

Criação, encerramento, invalidação e alteração de intenção são auditados. Dados de
intenção política são sensíveis: isolamento por tenant, permissão operacional e
retenção definida no cadastro.
