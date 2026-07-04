# SPEC-05 - Territorios e Georreferenciamento

Prioridade principal: P1  
Modulo: `mod_territorio`, `global`, `frontend_core/territorios`  
Objetivo: organizar a campanha por estado, municipio, bairro, zona, secao, local de votacao, microrregiao e area customizada, preparando mapas e filtros territoriais.

Status: base MVP entregue em 2026-07-03. A auditoria de aderencia identificou
entregas parciais em TER-009, TER-015, TER-018, TER-020, TER-022, TER-024 e
TER-027 a TER-029. As correcoes e evolucoes futuras foram consolidadas na
`SPEC-18-aprimoramentos-territorios-georreferenciamento-pos-mvp.md`.

## Escopo MVP

- Consulta de estados, municipios, bairros, zonas, secoes e locais de votacao.
- CRUD de territorios operacionais.
- Hierarquia territorial.
- Vinculo de pessoas e liderancas a territorios.
- Politica de acesso territorial para usuarios.
- Geocodificacao manual ou por coordenadas ja existentes.

## Fora do MVP

- Geocodificacao automatica em massa.
- Mapas de calor.
- Poligonos complexos editaveis.
- Integra cao automatica TSE/IBGE.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| TER-001 | P1 | Backend | Mapear tabelas globais de territorio eleitoral. | Models/schemas existem para estado, municipio, bairro, zona, local e secao. |
| TER-002 | P1 | Backend | Criar endpoint `GET /global/estados`. | Lista UFs ativas. |
| TER-003 | P1 | Backend | Criar endpoint `GET /global/municipios`. | Filtra por UF e nome. |
| TER-004 | P1 | Backend | Criar endpoint `GET /global/bairros`. | Filtra por municipio e nome. |
| TER-005 | P1 | Backend | Criar endpoint `GET /global/zonas-eleitorais`. | Filtra por UF/municipio. |
| TER-006 | P1 | Backend | Criar endpoint `GET /global/locais-votacao`. | Filtra por municipio, bairro, zona e nome. |
| TER-007 | P1 | Backend | Criar endpoint `GET /global/secoes-eleitorais`. | Filtra por zona e local de votacao. |
| TER-008 | P1 | Backend | Mapear `tipo_territorio` e `territorio`. | Entidades operacionais estao disponiveis no backend. |
| TER-009 | P1 | Backend | Criar CRUD de tipos de territorio. | Gestor administra tipos quando autorizado. |
| TER-010 | P1 | Backend | Criar CRUD de territorio operacional. | Territorio pode representar cidade, bairro, zona, secao, microrregiao ou area customizada. |
| TER-011 | P1 | Backend | Implementar hierarquia territorial. | Territorio pode ter pai/filho sem ciclos. |
| TER-012 | P1 | Backend | Criar endpoint para arvore territorial. | Frontend recebe hierarquia consolidada do tenant. |
| TER-013 | P1 | Backend | Vincular pessoa a territorio. | Pessoa pode ter territorio de moradia, votacao, atuacao ou responsabilidade. |
| TER-014 | P1 | Backend | Vincular lideranca a territorio. | Lider/coordenador pode ter territorios sob responsabilidade. |
| TER-015 | P1 | Backend | Aplicar politica territorial em consultas de cadastro. | Coordenador ve apenas pessoas nos territorios permitidos. |
| TER-016 | P1 | Backend | Registrar coordenadas manuais em endereco. | Lat/long salvos em endereco quando informados. |
| TER-017 | P1 | Backend | Registrar geocodificacao em tabela propria. | Resultado possui provedor, precisao, status e alvo. |
| TER-018 | P1 | Backend | Criar filtro territorial padrao reutilizavel. | Cadastro, metas, agenda e demandas usam filtro comum. |
| TER-019 | P1 | Frontend | Criar tela de territorios. | Lista, cria, edita e inativa territorios operacionais. |
| TER-020 | P1 | Frontend | Criar componente de seletor territorial. | Usado em cadastro, lideranca, metas, agenda e demandas. |
| TER-021 | P1 | Frontend | Criar arvore territorial. | Usuario visualiza hierarquia e filhos. |
| TER-022 | P1 | Frontend | Criar associacao de lideranca a territorio. | Gestor define areas de responsabilidade do lider. |
| TER-023 | P1 | Frontend | Criar campos de zona, secao e local de votacao no cadastro. | Formulario busca opcoes globais. |
| TER-024 | P1 | QA | Testar filtro territorial por perfil. | Coordenador nao acessa territorio fora da permissao. |
| TER-025 | P1 | QA | Testar hierarquia sem ciclos. | API rejeita ciclo territorial. |
| TER-026 | P2 | Jobs | Criar job de geocodificacao automatica de enderecos pendentes. | Job consulta provedor configurado e atualiza status. |
| TER-027 | P2 | Backend | Criar endpoint de mapa com marcadores agregados. | Retorna pontos de pessoas, eventos e demandas por filtro. |
| TER-028 | P2 | Frontend | Criar mapa Leaflet basico. | Usuario filtra marcadores por tipo, territorio e lider. |
| TER-029 | P2 | Frontend | Criar clusterizacao de marcadores. | Mapa permanece utilizavel com volume medio. |
| TER-030 | P3 | Frontend | Criar mapas de calor com Mapbox/WebGL quando necessario. | Grandes volumes renderizam sem travar. |

## Regras de negocio

- Territorios operacionais pertencem ao tenant.
- Tabelas oficiais de estado, municipio, zona, secao e local de votacao sao globais.
- Acesso territorial deve ser aplicado junto com permissao de perfil.
- Geocodificacao deve registrar provedor, precisao e status para auditoria tecnica.
- Mapa nao deve expor dados sensiveis para perfis sem permissao.

## Entidades principais

- `global.estado`
- `global.municipio`
- `global.bairro`
- `global.zona_eleitoral`
- `global.local_votacao`
- `global.secao_eleitoral`
- `territorio.tipo_territorio`
- `territorio.territorio`
- `territorio.territorio_hierarquia`
- `territorio.pessoa_territorio`
- `territorio.lideranca_territorio`
- `territorio.geocodificacao`
- `territorio.area_mapa`
- `auth.politica_acesso_territorial`

## Definition of Done

- Cadastro e consultas usam filtros territoriais.
- Liderancas podem ter territorios de atuacao.
- Usuarios territoriais respeitam escopo permitido.
- Coordenadas podem ser salvas e preparadas para mapa.
- Estrutura suporta geocodificacao e mapas na V2.
