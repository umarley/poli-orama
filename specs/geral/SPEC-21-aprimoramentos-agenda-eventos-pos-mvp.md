# SPEC-21 - Aprimoramentos de agenda e eventos pos-MVP

Status: backlog  
Prioridade principal: P2/P3  
Origem: pendencias AGE-019, AGE-028, AGE-031 e AGE-033 da SPEC-08  
Modulos: `backend_core/mod_agenda`, `backend_jobs_celery`, `frontend_core/agenda`

## Objetivo

Completar a experiencia de filtros por periodo, ampliar a cobertura automatizada
do CRUD e calendario, tornar os lembretes consumiveis pelo usuario e corrigir a
analise de temas para considerar convites independentemente da existencia de
pautas.

## Tarefas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| AGE-019A | P2 | Frontend | Adicionar filtro explicito por intervalo de datas. | Usuario informa inicio e fim nas visoes mensal, semanal e lista; o intervalo aparece nos parametros de `GET /agenda/eventos` e pode ser limpo sem perder os demais filtros. |
| AGE-019B | P2 | Frontend | Sincronizar periodo, navegacao e exportacao. | Navegar no calendario atualiza o periodo; intervalo manual atualiza a visualizacao; exportacao usa exatamente periodo, territorio, lider, tipo e status ativos. |
| AGE-028A | P1 | QA | Testar edicao completa de evento. | Teste integrado executa `PATCH /agenda/eventos/{id}`, valida auditoria e confirma alteracoes de titulo, datas, local, responsavel, territorio, tipo e status. |
| AGE-028B | P1 | QA | Testar calendario e detalhe no frontend. | Teste de interface cria ou simula evento, confirma sua exibicao nas visoes mensal, semanal e lista e abre o detalhe correto. |
| AGE-028C | P2 | QA | Testar cancelamento e restricoes de edicao. | Testes cobrem motivo obrigatorio, segundo cancelamento, evento inexistente, tenant diferente e usuario sem permissao. |
| AGE-031A | P2 | Backend | Criar endpoints de lembretes do usuario. | API lista apenas lembretes do usuario e tenant atuais, permite marcar como lido e retorna contagem de nao lidos. |
| AGE-031B | P2 | Frontend | Exibir central de lembretes da agenda. | Sino de notificacoes mostra eventos proximos, horario, local e link para o detalhe; usuario marca item ou todos como lidos. |
| AGE-031C | P2 | Jobs | Completar ciclo de vida dos lembretes. | Job cancela lembretes de eventos cancelados/remarcados, evita duplicidade e respeita antecedencia e habilitacao configuradas por tenant. |
| AGE-031D | P2 | QA | Testar lembretes ponta a ponta. | Testes cobrem geracao, idempotencia, isolamento por usuario/tenant, leitura, cancelamento e exibicao no frontend. |
| AGE-033A | P3 | Jobs | Analisar convites sem pauta associada. | Convites sao processados por consulta independente; evento com convite e nenhuma pauta pode gerar tema recorrente. |
| AGE-033B | P3 | Jobs | Evitar multiplicacao de textos por joins. | Cada pauta e convite e analisado uma vez, mesmo quando o evento possui varios registros de ambos os tipos. |
| AGE-033C | P3 | Jobs | Evoluir extracao e classificacao de temas. | Pipeline normaliza variacoes, registra algoritmo/versao e distingue palavra-chave, tema recorrente e demanda recorrente com score explicavel. |
| AGE-033D | P3 | QA | Cobrir NLP de pautas, convites e demandas. | Testes isolados validam pauta sem convite, convite sem pauta, multiplos convites/pautas, acentos, stop words, frequencia minima e reprocessamento idempotente. |

## Regras de negocio

- Filtros manuais devem ter precedencia explicita sobre o periodo padrao da
  visualizacao.
- Data final deve ser posterior a data inicial.
- Lembretes devem respeitar tenant, usuario, permissao territorial e permissao
  `agenda.visualizar`.
- Usuario nao pode ler ou alterar lembrete pertencente a outro usuario.
- Evento cancelado nao pode manter lembrete ativo.
- Remarcacao deve cancelar o lembrete anterior e gerar outro para o novo horario.
- Analise de texto nao pode depender da existencia simultanea de pauta e convite.
- Reprocessamento dos insights deve ser idempotente e registrar versao do
  algoritmo.

## Definition of Done

- Filtro de intervalo funciona nas tres visoes e na exportacao.
- Edicao e calendario possuem testes automatizados de API e frontend.
- Lembretes aparecem na interface, podem ser lidos e acompanham cancelamentos e
  remarcacoes.
- Convites independentes geram insights sem duplicacao de frequencia.
- Testes de backend, jobs e frontend passam sem regressao.

