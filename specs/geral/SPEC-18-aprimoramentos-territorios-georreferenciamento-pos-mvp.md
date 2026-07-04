# SPEC-18 - Aprimoramentos de Territorios e Georreferenciamento Pos-MVP

Prioridade principal: P2  
Modulos: `mod_territorio`, `mod_cadastro`, `mod_metas`, `mod_agenda`,
`mod_demandas`, `backend_jobs_celery`, `frontend_core/territorios`  
Origem: auditoria de aderencia da
`SPEC-05-territorios-georreferenciamento.md`  
Data da auditoria: 2026-07-03  
Status: backlog futuro

## Objetivo

Concluir os itens entregues parcialmente na SPEC-05 e evoluir o modulo
territorial com geocodificacao automatica, mapas multientidade, clusterizacao
dinamica, areas editaveis e importacao controlada de referencias oficiais.

Esta SPEC nao reabre a base MVP que ja esta operacional. Ela concentra lacunas
de aderencia, seguranca e funcionalidades explicitamente classificadas como
pos-MVP na SPEC-05.

## Resultado da auditoria da SPEC-05

| Item | Situacao | Evidencia ou lacuna |
| --- | --- | --- |
| TER-001 | Concluido | Models e schemas existem para estado, municipio, bairro, zona, local e secao. |
| TER-002 | Concluido | `GET /global/estados` implementado. |
| TER-003 | Concluido | `GET /global/municipios` filtra por estado e nome. |
| TER-004 | Concluido | `GET /global/bairros` filtra por municipio e nome. |
| TER-005 | Concluido | `GET /global/zonas-eleitorais` filtra por estado e municipio. |
| TER-006 | Concluido | `GET /global/locais-votacao` possui os filtros previstos. |
| TER-007 | Concluido | `GET /global/secoes-eleitorais` filtra por zona e local. |
| TER-008 | Concluido | `tipo_territorio` e `territorio` estao mapeados. |
| TER-009 | Parcial | Backend lista, cria e altera tipos, mas nao possui exclusao explicita. Frontend apenas lista e cria; nao edita nem inativa tipos customizados. |
| TER-010 | Concluido no MVP | CRUD operacional suporta referencias oficiais e inativacao. Edicao visual de poligono permanece fora do MVP. |
| TER-011 | Concluido | Pai unico e deteccao de ciclos implementados. |
| TER-012 | Concluido | Endpoint e arvore visual implementados. |
| TER-013 | Concluido no backend | Vinculo e desvinculo de pessoa existem. Falta interface de administracao e consulta dos vinculos. |
| TER-014 | Concluido no backend | Vinculo e desvinculo de lideranca existem. A interface cria vinculo, mas nao lista nem remove responsabilidades existentes. |
| TER-015 | Parcial | Filtro territorial foi aplicado a lista, busca rapida e detalhe de pessoa. Grafo de indicacoes, listagem de liderancas e outras consultas ainda podem retornar dados fora do escopo. |
| TER-016 | Concluido no backend | Latitude/longitude sao aceitas e o ponto PostGIS e sincronizado. Nao existe captura visual dedicada ou selecao pelo mapa. |
| TER-017 | Concluido no nivel basico | Registro manual possui alvo, provedor, precisao e status. Faltam consulta, revisao, validacao do alvo e sincronizacao do resultado com a entidade de origem. |
| TER-018 | Parcial | Existe resolucao reutilizavel de territorios acessiveis, mas somente cadastro e territorio a utilizam. Metas, agenda e demandas ainda nao aplicam o filtro comum. |
| TER-019 | Concluido | Tela lista, cria, edita e inativa territorios. |
| TER-020 | Parcial | `TerritorySelect` existe apenas no filtro de cadastro. Lideranca, metas, agenda e demandas ainda nao utilizam o componente. |
| TER-021 | Concluido | Arvore territorial disponivel no frontend. |
| TER-022 | Parcial | Gestor associa uma lideranca, mas nao visualiza, altera ou remove os vinculos existentes pela interface. |
| TER-023 | Concluido no cadastro inicial | Zona, local e secao usam referencias globais no assistente de cadastro. A edicao posterior deve reutilizar o mesmo fluxo. |
| TER-024 | Parcial | Ha teste de isolamento na listagem de territorios e teste unitario do objeto de acesso. Falta provar isolamento de pessoas e demais consultas/mutacoes reais. |
| TER-025 | Concluido | Testes unitario e de integracao rejeitam ciclos. |
| TER-026 | Nao implementado | Nao existe job de geocodificacao automatica. |
| TER-027 | Parcial | Endpoint agrega apenas pessoas e filtra apenas por territorio. Eventos, demandas, lideranca, tipo e periodo nao foram implementados. |
| TER-028 | Parcial | Mapa Leaflet existe, mas o usuario filtra somente por territorio. |
| TER-029 | Parcial | Existe agregacao fixa por coordenadas arredondadas no backend, nao clusterizacao dinamica de marcadores conforme zoom e volume. |
| TER-030 | Nao implementado | Nao existe mapa de calor Mapbox/WebGL. |

## Escopo de correcao de aderencia

- Completar administracao de tipos territoriais.
- Aplicar escopo territorial a todas as operacoes que consultam ou alteram
  entidades territorializadas.
- Transformar o filtro territorial em componente backend comum para cadastro,
  metas, agenda e demandas.
- Reutilizar o seletor territorial nos formularios dos modulos consumidores.
- Completar administracao visual dos vinculos de pessoas e liderancas.
- Completar o mapa multientidade e seus filtros.
- Ampliar testes positivos e negativos por perfil, modulo e descendencia.

## Escopo pos-MVP

- Geocodificacao automatica assincrona.
- Revisao e reprocessamento de geocodificacoes.
- Poligonos e areas customizadas editaveis.
- Importacao automatizada e versionada de referencias IBGE/TSE.
- Clusterizacao dinamica e mapas de calor.
- Observabilidade, limites de provedor e protecao de dados nos mapas.

## Fora do escopo

- Rastreamento em tempo real de dispositivos da equipe.
- Inferencia de voto individual ou acesso a dados oficiais individuais de voto.
- Exposicao de nomes, contatos ou enderecos completos em agregados de mapa.
- Substituicao de bases oficiais sem versionamento, fonte e data de referencia.

## Tarefas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| TER18-001 | P1 | Backend | Completar CRUD de tipos customizados de territorio. | Gestor cria, edita, inativa e reativa apenas tipos do proprio tenant; tipos globais permanecem imutaveis. |
| TER18-002 | P1 | Frontend | Completar tela de tipos territoriais. | Usuario autorizado edita, inativa e reativa tipos customizados com feedback de conflito e uso. |
| TER18-003 | P1 | Backend | Extrair filtro territorial reutilizavel para consultas e mutacoes. | Helper comum aplica tenant, perfil, escopos oficiais, territorio operacional e descendentes sem duplicar SQL por modulo. |
| TER18-004 | P1 | Cadastro | Fechar isolamento territorial do cadastro. | Lista, busca, detalhe, grafo, liderancas, exportacoes e mutacoes bloqueiam registros fora do escopo. |
| TER18-005 | P1 | Metas | Aplicar filtro territorial comum em metas e rankings. | Coordenador lista e altera somente metas dos territorios autorizados. |
| TER18-006 | P1 | Agenda | Aplicar filtro territorial comum em eventos e agenda. | Consultas, convites, presencas e mutacoes respeitam o escopo territorial. |
| TER18-007 | P1 | Demandas | Aplicar filtro territorial comum em demandas e atendimentos. | Consultas, atribuicoes, movimentacoes e exportacoes respeitam o escopo territorial. |
| TER18-008 | P1 | Frontend | Adotar `TerritorySelect` nos modulos consumidores. | Cadastro, lideranca, metas, agenda e demandas usam o seletor comum e exibem apenas opcoes permitidas. |
| TER18-009 | P1 | Backend | Criar endpoints de consulta dos vinculos territoriais. | API lista vinculos por pessoa, lideranca e territorio com paginacao e escopo de acesso. |
| TER18-010 | P1 | Frontend | Administrar vinculos de pessoas e liderancas. | Gestor visualiza, cria, altera responsabilidade/vinculo e remove associacoes existentes. |
| TER18-011 | P1 | Frontend | Reutilizar campos eleitorais na edicao de pessoa. | Edicao posterior de eleitor oferece zona, local e secao dependentes, sem entrada numerica manual. |
| TER18-012 | P1 | QA | Ampliar matriz de testes territoriais reais. | Testes cobrem gestor, coordenador, lider e telefonista em lista, detalhe, criacao, edicao, exclusao e exportacao de cada modulo aplicavel. |
| TER18-013 | P2 | Backend | Completar gestao de geocodificacoes. | API lista pendencias, detalha tentativas, revisa resultado, reprocessa e valida que o alvo pertence ao tenant. |
| TER18-014 | P2 | Backend | Sincronizar resultado de geocodificacao com o alvo. | Sucesso atualiza coordenadas/geom e status da entidade de origem de forma transacional e auditavel. |
| TER18-015 | P2 | Jobs | Implementar job automatico de geocodificacao. | Celery busca enderecos pendentes em lotes, consulta provedor configurado, respeita rate limit e atualiza resultado. |
| TER18-016 | P2 | Jobs | Implementar idempotencia, retry e fila de revisao. | Falhas transitorias usam backoff; falhas definitivas nao entram em loop; baixa precisao segue para revisao manual. |
| TER18-017 | P2 | Configuracao | Configurar provedores de geocodificacao por ambiente. | Chaves ficam fora do banco/log, provedor pode ser desabilitado e ambiente de teste usa fake deterministico. |
| TER18-018 | P2 | Backend | Evoluir endpoint de marcadores para multientidade. | Retorna agregados de pessoas, eventos e demandas com filtros por tipo, territorio, lider, status e periodo. |
| TER18-019 | P2 | Seguranca | Aplicar minimizacao e limiar de anonimato no mapa. | Perfis operacionais recebem apenas agregados; grupos abaixo do limiar configurado nao revelam localizacao precisa. |
| TER18-020 | P2 | Frontend | Completar filtros do mapa. | Usuario filtra tipo de marcador, territorio, lider, status e periodo; filtros aparecem na URL e podem ser limpos. |
| TER18-021 | P2 | Frontend | Implementar clusterizacao dinamica. | Marcadores sao reagrupados conforme zoom/viewport e o mapa permanece responsivo com volume medio definido em teste. |
| TER18-022 | P2 | Backend | Criar CRUD de `area_mapa`. | API cria, valida, lista, altera e inativa GeoJSON Polygon/MultiPolygon dentro do tenant. |
| TER18-023 | P2 | Frontend | Criar editor de areas customizadas. | Usuario autorizado desenha, edita e valida poligonos no mapa sem produzir geometrias invalidas. |
| TER18-024 | P2 | ETL | Importar referencias IBGE/TSE de forma versionada. | Pipeline registra fonte, versao, checksum, data, inclusoes, alteracoes, inativacoes e erros sem duplicar referencias. |
| TER18-025 | P2 | QA | Testar geocodificacao, mapa e poligonos. | Testes cobrem idempotencia, rate limit, falha de provedor, geometria invalida, RLS e mascaramento. |
| TER18-026 | P3 | Frontend | Implementar mapa de calor WebGL. | Camada pode ser ativada por metrica autorizada e renderiza o volume de referencia sem bloquear a interface. |
| TER18-027 | P2 | Observabilidade | Instrumentar geocodificacao e mapas. | Metricas informam fila, latencia, taxa de sucesso, custo estimado, cache, volume de pontos e falhas por provedor. |

## Regras de negocio

- Escopo territorial nunca substitui RBAC; ambos devem autorizar a operacao.
- Acesso a um territorio operacional inclui seus descendentes, respeitando o
  nivel de administracao concedido.
- Vinculos e referencias devem pertencer ao mesmo tenant quando aplicavel.
- Geocodificacao automatica deve ser opt-in por ambiente e tenant.
- Toda tentativa de geocodificacao deve preservar provedor, precisao, status,
  horario e erro tecnico sanitizado.
- Coordenadas precisas e enderecos nao podem aparecer em agregados para perfis
  que nao necessitam desse nivel de detalhe.
- Importacoes IBGE/TSE nunca devem apagar silenciosamente referencias usadas
  por dados historicos.
- GeoJSON recebido deve ter SRID 4326, limites de tamanho e geometria valida.

## Dependencias

- SPEC-06 para filtros em metas e rankings.
- SPEC-08 para filtros em agenda e eventos.
- SPEC-09 para filtros em demandas e atendimentos.
- SPEC-11 para armazenamento de arquivos de importacao.
- SPEC-16 para matriz RBAC final, mascaramento, auditoria e observabilidade.
- Provedor de geocodificacao e politica comercial/juridica aprovados.
- Fonte, licenca e rotina de atualizacao das bases IBGE/TSE definidas.

## Estrategia de entrega

### Fase 1 - Fechamento de aderencia e seguranca

- TER18-001 a TER18-012.
- Deve ser concluida antes de considerar o isolamento territorial pronto para
  producao.

### Fase 2 - Geocodificacao e mapa V2

- TER18-013 a TER18-021 e TER18-027.
- Deve iniciar com provedor fake e testes de idempotencia antes da integracao
  externa.

### Fase 3 - Areas e dados oficiais

- TER18-022 a TER18-025.
- Requer definicao de fonte, licenca, volume e frequencia de atualizacao.

### Fase 4 - Visualizacao avancada

- TER18-026.
- So deve ser priorizada depois de metricas reais demonstrarem necessidade.

## Definition of Done

- Nenhuma consulta ou mutacao territorializada ignora o escopo efetivo do
  usuario.
- Seletor e administracao de vinculos sao reutilizados nos modulos previstos.
- Geocodificacao automatica e idempotente, observavel, auditavel e resiliente a
  falhas do provedor.
- Mapa suporta pessoas, eventos e demandas sem expor dados sensiveis.
- Clusterizacao atende ao volume de referencia acordado.
- Areas customizadas aceitam apenas geometrias validas e isoladas por tenant.
- Importacoes oficiais sao versionadas e reproduziveis.
- Testes positivos e negativos comprovam RBAC, RLS, descendencia e mascaramento.
