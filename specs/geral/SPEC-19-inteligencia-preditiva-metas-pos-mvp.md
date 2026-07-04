# SPEC-19 - Inteligencia Preditiva de Metas Pos-MVP

Prioridade principal: P3  
Modulo: `mod_metas`, `backend_jobs_celery`, `frontend_core/metas`  
Origem: evolucao da META-030 e dos itens fora do MVP da SPEC-06.

## Objetivo

Substituir ou complementar a heuristica explicavel de risco por um modelo
estatistico treinado, calibrado e monitorado, sem remover o fallback
deterministico usado no MVP.

## Pre-condicoes

- Historico suficiente de metas, acompanhamentos e resultados operacionais.
- Definicao de rotulo de risco que nao confunda confirmacao operacional com
  comprovacao oficial de voto.
- Politica de retencao, anonimizacao e uso de dados aprovada.
- Volume minimo por tenant ou estrategia segura de modelo agregado.

## Tarefas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| META-ML-001 | P3 | Dados | Definir dataset e rotulo de treinamento. | Dataset possui dicionario, janela temporal e prevencao de vazamento de dados. |
| META-ML-002 | P3 | ETL | Criar pipeline de features versionado. | Features de historico, engajamento, cobertura e velocidade sao reproduziveis. |
| META-ML-003 | P3 | ML | Treinar modelo baseline e candidatos. | Metricas sao comparadas com a heuristica atual. |
| META-ML-004 | P3 | ML | Calibrar probabilidades de risco. | Score possui calibracao validada e faixas operacionais documentadas. |
| META-ML-005 | P3 | Backend | Versionar modelo e predicoes. | Cada predicao registra versao, fatores, horario e origem dos dados. |
| META-ML-006 | P3 | Seguranca | Garantir isolamento por tenant. | Nenhum dado identificavel de um tenant aparece na predicao de outro. |
| META-ML-007 | P3 | Backend | Manter fallback heuristico. | Falha ou baixa confianca do modelo utiliza `heuristica_v1`. |
| META-ML-008 | P3 | Frontend | Exibir explicacao e confianca. | Usuario visualiza fatores, confianca e versao sem interpretacao enganosa. |
| META-ML-009 | P3 | MLOps | Monitorar drift e qualidade. | Alertas identificam degradacao, mudanca de distribuicao e dados incompletos. |
| META-ML-010 | P3 | QA | Validar retrospectivamente e por tenant. | Testes cobrem calibracao, vies, isolamento e reproducibilidade. |
| META-ML-011 | P2 | Eventos | Avaliar recalculo orientado a eventos. | Alteracoes cadastrais podem disparar atualizacao imediata sem duplicar jobs. |
| META-ML-012 | P3 | Notificacoes | Criar notificacoes de risco em tempo real. | Canais, preferencias, idempotencia e auditoria estao definidos. |

## Fora deste escopo

- Comprovacao oficial de voto individual.
- Inferencia de preferencia politica sensivel sem base legal.
- Integracao com resultado eleitoral oficial, tratada no modulo de eleicao.
- Gamificacao avancada sem especificacao propria.

## Definition of Done

- Modelo supera ou complementa a heuristica com evidencia mensuravel.
- Predicoes sao explicaveis, versionadas, auditaveis e isoladas por tenant.
- Fallback heuristico permanece funcional.
- Monitoramento de qualidade e drift esta ativo.
