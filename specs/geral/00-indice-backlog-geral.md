# Backlog Geral - SaaS de Inteligencia Politica

Status: backlog inicial  
Data: 2026-06-25  
Escopo: frontend autenticado, backend principal, jobs assincronos, site publico, qualidade, seguranca e operacao.

## Fontes analisadas

- `docs/CONTEXTO_IA_INTELIGENCIA_POLITICA.md`
- `docs/arquitetura_solu*.md`
- `docs/estrutura_backlog.md`
- `docs/estrutura_banco_dados.md`
- `docs/estrutura_site_publico.md`
- `docs/TRANSCRICAO_PLATAFORMA_POLITIQUE.md`
- `docs/RELATORIO SISTEMA.pdf`
- `docs/Plano_Necessidades_Inteligencia_Politica 2026 (1).docx`
- `app_saas/database/migrations/001 - ddl_inteligencia_politica.sql`
- `app_saas/database/docs/dicionario_dados_inteligencia_politica.md`

## Premissas

- O banco de dados e o modelo de dados ja existem.
- O backend principal sera construido em `app_saas/backend_core` com FastAPI.
- Os jobs e ETLs ficarao em `app_saas/backend_jobs_celery`.
- O painel autenticado sera construido em `app_saas/frontend_core` com React + Vite.
- O site publico sera separado em `app_saas/site_publico` com Astro + React.
- A estrategia inicial de multitenancy usa `tenant_id` e RLS no PostgreSQL.
- O MVP deve priorizar operacao real da campanha: cadastro, liderancas, metas, importacao, dashboard inicial, seguranca e auditoria.

## Priorizacao

| Prioridade | Uso | Regra |
| --- | --- | --- |
| P0 | Fundacao do MVP | Bloqueia desenvolvimento ou seguranca do produto. Deve ser feito primeiro. |
| P1 | MVP funcional | Entrega valor operacional direto para campanha. Deve entrar no primeiro release. |
| P2 | Pos-MVP / V2 | Aumenta eficiencia, mapas, automacoes, anexos e experiencia mobile. |
| P3 | V3 / inteligencia avancada | NLP, ML, redes sociais, modo eleicao completo e BI avancado. |

## Sequencia recomendada do MVP

1. SPEC-01 - Fundacao tecnica e arquitetura modular.
2. SPEC-02 - Tenants, planos, onboarding e configuracoes.
3. SPEC-03 - Autenticacao, autorizacao, RLS e auditoria.
4. SPEC-04 - Cadastro de pessoas, eleitores, liderancas e vinculos.
5. SPEC-05 - Territorios e georreferenciamento basico.
6. SPEC-06 - Metas de votos, rankings e alertas iniciais.
7. SPEC-07 - Importacao, ETL inicial e qualidade de dados.
8. SPEC-10 - Dashboards e relatorios basicos.
9. SPEC-08 - Agenda e eventos em versao enxuta.
10. SPEC-09 - Demandas e atendimentos em versao enxuta.
11. SPEC-11 a SPEC-15 - Modulos complementares e avancados conforme o release.
12. SPEC-16 - Fechamento final de seguranca, LGPD, observabilidade, QA e deploy,
    executado depois de todas as demais specs previstas.

## Arquivos de specs

| Spec | Tema | Prioridade principal |
| --- | --- | --- |
| `SPEC-01-fundacao-tecnica-arquitetura.md` | Base tecnica, monolito modular, frontend shell, jobs e CI | P0 |
| `SPEC-02-tenants-planos-onboarding.md` | SaaS, tenants, planos, configuracao e ativacao inicial | P0 |
| `SPEC-03-auth-rbac-rls-auditoria.md` | Login, perfis, permissoes, RLS e trilha de auditoria | P0 |
| `SPEC-04-cadastro-pessoas-eleitores-liderancas.md` | Cadastro central, eleitores, liderancas, hierarquia e duplicidade | P1 |
| `SPEC-05-territorios-georreferenciamento.md` | Territorios, zonas, secoes, acesso territorial e geocodificacao | P1 |
| `SPEC-06-metas-votos-rankings-alertas.md` | Metas por lider, territorio, equipe e acompanhamento | P1 |
| `SPEC-07-importacao-etl-qualidade-dados.md` | CSV/Excel, staging, deduplicacao, validacoes e logs | P1 |
| `SPEC-08-agenda-eventos.md` | Agenda politica, eventos, convites, presenca e pautas | P1 |
| `SPEC-09-demandas-atendimentos.md` | Demandas, responsaveis, prazos, status e movimentacoes | P1 |
| `SPEC-10-dashboards-relatorios.md` | KPIs, relatorios basicos, filtros e exportacoes controladas | P1 |
| `SPEC-11-arquivos-anexos-datalake.md` | Upload, storage, anexos, fotos, convites e documentos | P2 |
| `SPEC-12-site-publico-comercial.md` | Site publico, SEO, leads, planos e contratacao | P1 |
| `SPEC-12B-site-publico-pos-mvp.md` | Blog, cases e checkout real do site publico | P2 |
| `SPEC-13-comunicacao-datas-redes.md` | Interacoes, datas comemorativas, comunicacao e redes sociais | P2/P3 |
| `SPEC-13B-comunicacao-datas-redes-pos-mvp.md` | Consentimento, campanhas e integracoes sociais pos-MVP | P2/P3 |
| `SPEC-14-modo-eleicao.md` | Operacao do dia da votacao e acompanhamento operacional | P3 |
| `SPEC-15-nlp-ml-inteligencia-avancada.md` | Classificacao, previsoes, score de risco e recomendacoes | P3 |
| `SPEC-16-qualidade-seguranca-lgpd-deploy.md` | Testes, LGPD, observabilidade, backup, deploy e go-live | P0/P1 |
| `SPEC-17-aprimoramentos-cadastro-pos-mvp.md` | Qualidade cadastral, duplicidades, historico e auditoria complementar | P1/P2 |
| `SPEC-18-aprimoramentos-territorios-georreferenciamento-pos-mvp.md` | Fechamento territorial, geocodificacao automatica, mapas e dados oficiais | P1/P2/P3 |
| `SPEC-19-inteligencia-preditiva-metas-pos-mvp.md` | Modelo treinado, explicabilidade, fallback e monitoramento de risco | P2/P3 |
| `SPEC-20-integracoes-etl-avancadas-pos-mvp.md` | GESPED automatico, dados oficiais TSE/IBGE e OCR | P2/P3 |
| `SPEC-21-aprimoramentos-agenda-eventos-pos-mvp.md` | Filtros, QA, lembretes e analise de temas da agenda | P1/P2/P3 |
| `SPEC-22-aprimoramentos-demandas-atendimentos-pos-mvp.md` | Cadastro rapido de solicitante, filtros, QA, responsaveis e NLP de demandas | P2/P3 |

## MVP minimo recomendado

O MVP minimo deve permitir que um tenant real:

- Acesse o sistema com usuarios, perfis e permissoes basicas.
- Cadastre pessoas, eleitores, lideres, liderados, contatos, enderecos e dados eleitorais.
- Evite ou sinalize duplicidade por CPF, titulo, telefone, e-mail e nome/data de nascimento.
- Vincule pessoas a lideres, coordenadores, tags, comunidades e nucleos familiares.
- Cadastre territorios e associe pessoas/liderancas a cidade, bairro, zona, secao ou regiao.
- Defina metas por lider e territorio.
- Importe planilhas CSV/Excel de pessoas.
- Visualize KPIs iniciais de cadastro, liderancas, metas, demandas e eventos.
- Registre agenda/eventos e demandas em primeira versao, ainda sem automacoes avancadas.
- Audite acoes sensiveis e controle exportacoes.

## Fora do MVP minimo

- NLP automatico de demandas.
- ML para previsao de risco.
- Monitoramento automatico de Instagram ou WhatsApp.
- Modo eleicao em tempo real completo.
- Data Warehouse sofisticado e dashboards externos em BI.
- Geocodificacao massiva automatica com mapas de calor.
- Checkout completamente automatizado se o provedor de pagamento ainda nao estiver definido.

## Definition of Ready para uma tarefa

- Tem objetivo claro.
- Informa area impactada: backend, frontend, jobs, database, QA, produto ou devops.
- Declara prioridade P0, P1, P2 ou P3.
- Aponta entidade/tabela principal quando aplicavel.
- Tem criterio de aceite testavel.
- Tem dependencia explicita quando existir.

## Definition of Done geral

- Implementacao revisada e integrada no modulo correto.
- Testes unitarios ou de integracao criados para regras de negocio relevantes.
- Fluxo principal validado no frontend quando houver tela.
- Erros tratados com mensagens claras.
- Auditoria registrada quando a acao alterar dados sensiveis ou exportar informacoes.
- Respeito ao tenant atual validado em endpoints privados.
- Documentacao curta adicionada quando houver comportamento nao obvio.
