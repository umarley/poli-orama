# SPEC-14 - Modo Eleicao

Prioridade principal: P3  
Modulo: `mod_eleicao`, `frontend_core/eleicao`  
Objetivo: apoiar a operacao do dia da votacao com acompanhamento operacional por lider, territorio, zona, secao e local de votacao, sem representar comprovacao oficial de voto individual.

## Escopo futuro

- Cadastro da eleicao.
- Configuracao da operacao.
- Lista de eleitores por lider, local, zona e secao.
- Status operacional do eleitor.
- Confirmacao operacional informada por lider/equipe/eleitor.
- Ocorrencias do dia.
- Painel consolidado quase em tempo real.
- Auditoria completa.

## Fora do escopo legal/etico

- Comprovacao oficial individual de voto.
- Consulta a dados oficiais individuais de comparecimento se nao houver base legal e fonte permitida.
- Coacao, compra de voto ou uso indevido de dados sensiveis.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| ELE-001 | P3 | Produto/Juridico | Definir regra oficial de status operacional permitido. | Documento aprovado diferencia contato, confirmacao operacional e voto oficial. |
| ELE-002 | P3 | Produto/Juridico | Definir textos de conformidade do modo eleicao. | Interface evita promessa de comprovacao individual de voto. |
| ELE-003 | P3 | Backend | Mapear entidades de eleicao. | Models/schemas para eleicao, operacao, status, confirmacao, ocorrencia e snapshot. |
| ELE-004 | P3 | Backend | Criar CRUD de `eleicao`. | Gestor cadastra ano, tipo, turno, data e escopo. |
| ELE-005 | P3 | Backend | Criar CRUD de `operacao_eleicao`. | Gestor ativa/configura operacao por tenant e eleicao. |
| ELE-006 | P3 | Backend | Criar catalogo de status operacional. | Status nao contatado, contatado, confirmado, pendente, precisa de apoio e sem resposta. |
| ELE-007 | P3 | Backend | Gerar lista operacional por lider. | Lider visualiza eleitores vinculados e locais permitidos. |
| ELE-008 | P3 | Backend | Criar endpoint para atualizar status operacional. | Atualizacao registra usuario, data, origem e auditoria. |
| ELE-009 | P3 | Backend | Criar confirmacao operacional. | Registro explicita que nao e comprovacao oficial de voto. |
| ELE-010 | P3 | Backend | Criar ocorrencia de eleicao. | Lider/equipe registra transporte, contato, problema ou apoio. |
| ELE-011 | P3 | Backend | Criar painel consolidado por lider. | Retorna totais por status e alertas. |
| ELE-012 | P3 | Backend | Criar painel consolidado por territorio/zona/secao. | Gestor acompanha operacao por recorte eleitoral. |
| ELE-013 | P3 | Backend | Criar snapshot periodico. | `painel_eleicao_snapshot` guarda indicadores para historico. |
| ELE-014 | P3 | Backend | Criar canal de atualizacao quase em tempo real. | WebSocket/SSE/polling definido e implementado. |
| ELE-015 | P3 | Backend | Criar limites de taxa para atualizacao. | Sistema evita abuso em alto volume. |
| ELE-016 | P3 | Frontend | Criar tela de configuracao da operacao. | Gestor ativa/desativa modo eleicao e parametros. |
| ELE-017 | P3 | Frontend | Criar tela do lider. | Lider ve sua lista, filtros por local/zona/secao e status. |
| ELE-018 | P3 | Frontend | Criar atualizacao rapida de status. | Lider atualiza status com poucos toques no mobile. |
| ELE-019 | P3 | Frontend | Criar registro de ocorrencia. | Lider registra apoio ou problema vinculado ao eleitor/local. |
| ELE-020 | P3 | Frontend | Criar painel executivo. | Gestor ve totais por lider, territorio, zona e secao. |
| ELE-021 | P3 | Frontend | Criar alertas de baixa confirmacao operacional. | Lideres/territorios abaixo do esperado aparecem destacados. |
| ELE-022 | P3 | QA | Testar isolamento por lider. | Lider nao ve eleitores fora do seu escopo. |
| ELE-023 | P3 | QA | Testar concorrencia de atualizacoes. | Atualizacao simultanea preserva ultimo estado com historico. |
| ELE-024 | P3 | QA | Testar volume esperado. | Painel suporta carga simulada do dia da eleicao. |
| ELE-025 | P3 | Observabilidade | Criar monitoramento especifico do modo eleicao. | Latencia, erros e fila aparecem em painel tecnico. |

## Regras de negocio

- Modo eleicao deve ser ativado explicitamente por gestor autorizado.
- Toda atualizacao deve ser auditada.
- Status operacional deve ser reversivel com historico.
- Lider so acessa sua propria lista, salvo permissoes especiais.
- Coordenador acessa territorios permitidos.
- Sistema deve deixar claro que confirmacao operacional nao e comprovacao oficial de voto.

## Entidades principais

- `eleicao.eleicao`
- `eleicao.operacao_eleicao`
- `eleicao.status_eleitor_eleicao`
- `eleicao.confirmacao_operacional_voto`
- `eleicao.ocorrencia_eleicao`
- `eleicao.painel_eleicao_snapshot`
- `cadastro.eleitor`
- `cadastro.lideranca`
- `global.local_votacao`
- `global.zona_eleitoral`
- `global.secao_eleitoral`

## Definition of Done

- Regras juridicas e operacionais estao aprovadas.
- Lider usa fluxo mobile simples.
- Gestor ve painel consolidado.
- Atualizacoes sao auditadas e performaticas.
- Sistema nao afirma acesso a comprovacao oficial de voto individual.
