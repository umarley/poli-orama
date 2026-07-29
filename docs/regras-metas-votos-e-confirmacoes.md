# Regras de metas, votos projetados e confirmações

## Objetivo

O sistema contabiliza pessoas, e não lançamentos numéricos manuais. Cada pessoa pode
representar no máximo um voto projetado e um voto declarado como confirmado em uma
campanha eleitoral.

Uma confirmação operacional representa uma declaração de intenção de voto. Ela não
é prova de que o voto foi depositado na urna.

## Fontes oficiais

| Informação | Fonte |
|---|---|
| Pessoa cadastrada | `cadastro.pessoa` |
| Liderança responsável atual | `cadastro.hierarquia_lideranca` |
| Campanha | `eleicao.campanha_eleicao` |
| Situação atual do contato | `eleicao.status_eleitor_eleicao` |
| Declaração de voto | `eleicao.confirmacao_operacional_voto` |
| Histórico de contatos | `comunicacao.atendimento_eleitor` |
| Fotografias da evolução da meta | `meta.acompanhamento_meta` |

## Unicidade e atribuição

Uma pessoa possui somente uma liderança ativa por tenant. A restrição é garantida
pelo índice parcial `cadastro.uq_hierarquia_pessoa_ativa_tenant`.

Uma pessoa possui somente um estado e uma confirmação operacional por campanha:

- `UNIQUE (campanha_eleicao_id, pessoa_id)` em
  `eleicao.status_eleitor_eleicao`;
- `UNIQUE (campanha_eleicao_id, pessoa_id)` em
  `eleicao.confirmacao_operacional_voto`.

Essas restrições impedem que transferências de liderança, novas ligações ou várias
metas dupliquem a mesma pessoa.

Quando a pessoa muda de liderança, os novos resultados pertencem à liderança ativa.
O histórico de atendimentos conserva a liderança existente em cada ligação.

## Contabilização

### Eleitores vinculados e votos projetados

Para metas cujo alvo seja uma liderança:

```text
quantidade_eleitores_vinculados =
quantidade de pessoas com vínculo ativo com a liderança

quantidade_projetada =
quantidade_eleitores_vinculados
```

O cadastro de uma pessoa pelo aplicativo mobile deve criar ou associar o vínculo
ativo com a liderança autenticada. A pessoa entra imediatamente como voto possível,
mas não como voto confirmado.

Para outros tipos de alvo, a base continua sendo calculada pelas associações de
território, equipe, comunidade, núcleo familiar ou pessoa.

### Votos confirmados

```text
quantidade_confirmada =
quantidade de pessoas distintas da base da meta
com confirmação operacional positiva na campanha da eleição do período
e sem revogação
```

Uma confirmação só é criada ou atualizada por um atendimento. O total não pode ser
digitado no acompanhamento da meta.

### Progresso

```text
percentual_atingido =
quantidade_confirmada / quantidade_meta * 100
```

`quantidade_atual`, barras de progresso, risco, resumo e ranking usam a quantidade
confirmada. A projeção informa o tamanho da carteira do líder e não representa
atingimento.

## Fluxo do Call Center

1. A fila seleciona pessoas com vínculo ativo e apresenta seus dados de contato.
2. O atendente registra uma tentativa em
   `comunicacao.atendimento_eleitor`.
3. O sistema atualiza o estado atual em
   `eleicao.status_eleitor_eleicao`.
4. Quando o resultado é `confirmado`, o sistema grava a confirmação operacional.
5. Um resultado posterior explícito `indeciso` ou `nao_apoia` revoga a confirmação
   anterior. Tentativas sem resposta, retorno agendado e número inválido não apagam
   uma declaração já registrada.
6. As telas de metas passam a refletir o novo total na próxima consulta.

Estados disponíveis:

- `nao_contatado`;
- `tentativa_sem_resposta`;
- `retorno_agendado`;
- `indeciso`;
- `confirmado`;
- `nao_apoia`;
- `numero_invalido`.

## APIs preparadas

Todas as rotas são isoladas por tenant:

- `GET /api/v1/call-center/fila`;
- `POST /api/v1/call-center/atendimentos`;
- `GET /api/v1/call-center/relatorios/votos-confirmados`.

O relatório nominal retorna somente confirmações ativas e pode ser filtrado por
liderança. A fila pode ser filtrada por liderança e situação.

## Acompanhamento de metas

`meta.acompanhamento_meta` é histórico e não fonte primária. Ao registrar um
acompanhamento, o backend grava automaticamente:

- a projeção calculada pela base vinculada;
- a confirmação calculada pelas pessoas confirmadas;
- o percentual e a situação de risco.

Para a mesma meta e data, o registro é atualizado (`upsert`), evitando duas
fotografias concorrentes.

## Ranking de lideranças

O ranking utiliza pessoas distintas:

- `total_cadastros`: liderados ativos;
- `total_confirmacoes`: pessoas únicas confirmadas na campanha;
- `quantidade_atual`: confirmações das metas da liderança;
- `percentual_meta`: confirmações sobre a meta definida.

Uma pessoa nunca pode aumentar duas vezes o total da mesma campanha, mesmo que
possua vários atendimentos.

## Privacidade e auditoria

Dados de intenção política são sensíveis. As operações devem respeitar permissões,
isolamento por tenant, finalidade eleitoral informada, retenção definida e
auditoria. Relatórios nominais não devem ser expostos a perfis sem necessidade
operacional.
