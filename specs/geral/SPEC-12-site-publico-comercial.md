# SPEC-12 - Site Publico Comercial

Prioridade principal: P1  
Modulo: `site_publico`, `backend_core/api/public`  
Objetivo: criar o site publico do SaaS para apresentar a plataforma, capturar leads, exibir planos, iniciar contratacao e cumprir requisitos de SEO, LGPD e paginas legais.

## Escopo MVP

- Projeto Astro + React.
- Home, plataforma, planos, contratar, demo, contato e paginas legais.
- Paginas de recursos principais.
- SEO tecnico basico.
- Formularios de lead, demo, contato e contratacao.
- Captura de UTM.
- Integracao com APIs publicas do backend.
- Build estatico e deploy.

## Fora do MVP

- CMS externo.
- Blog robusto com calendario editorial completo.
- Checkout real se provedor nao estiver definido.
- Testes A/B.

## Tarefas pequenas

| ID | Prioridade | Area | Tarefa | Criterio de aceite |
| --- | --- | --- | --- | --- |
| SITE-001 | P1 | Frontend | Criar projeto Astro + React em `site_publico`. | `npm run dev` abre site publico. |
| SITE-002 | P1 | Frontend | Configurar TypeScript, sitemap e SEO base. | Build gera HTML, sitemap e metadados. |
| SITE-003 | P1 | Frontend | Criar layouts base, marketing, blog e legal. | Paginas usam layout consistente. |
| SITE-004 | P1 | Frontend | Criar tokens CSS e estilos globais. | Site possui visual profissional e responsivo. |
| SITE-005 | P1 | Frontend | Criar header, footer e navegacao. | Links para home, plataforma, planos, demo, contato e login. |
| SITE-006 | P1 | Frontend | Criar pagina home `/`. | Proposta de valor, beneficios, recursos, CTA e FAQ curta. |
| SITE-007 | P1 | Frontend | Criar pagina `/plataforma`. | Explica modulos e fluxo de dados. |
| SITE-008 | P1 | Frontend | Criar pagina `/planos`. | Tabela/comparador de planos e CTAs. |
| SITE-009 | P1 | Frontend | Criar pagina `/contratar`. | Formulario de pre-cadastro com aceite legal. |
| SITE-010 | P1 | Frontend | Criar pagina `/demo`. | Formulario enxuto para solicitacao de demonstracao. |
| SITE-011 | P1 | Frontend | Criar pagina `/contato`. | Formulario institucional e canais de suporte. |
| SITE-012 | P1 | Frontend | Criar paginas legais. | `/politica-de-privacidade`, `/termos-de-uso`, `/lgpd` existem. |
| SITE-013 | P1 | Frontend | Criar paginas de recursos. | Cadastro eleitoral, territorio/mapas, metas/liderancas, agenda/demandas, comunicacao e modo eleicao. |
| SITE-014 | P1 | Frontend | Criar pagina `404`. | Rota inexistente mostra pagina adequada. |
| SITE-015 | P1 | Frontend | Criar redirecionamento `/login`. | Redireciona para `PUBLIC_APP_LOGIN_URL`. |
| SITE-016 | P1 | Frontend | Criar dados estaticos de planos. | `src/data/planos.ts` reflete estrutura de `plano_assinatura`. |
| SITE-017 | P1 | Frontend | Integrar `GET /api/public/planos` quando disponivel. | Site usa API ou fallback estatico configuravel. |
| SITE-018 | P1 | Frontend | Criar schema Zod para lead. | Validacao client-side clara. |
| SITE-019 | P1 | Frontend | Criar formulario de lead/demo/contato. | Envia para `POST /api/public/leads`. |
| SITE-020 | P1 | Frontend | Criar schema Zod para contratacao. | Validacao de plano, ciclo, responsavel, organizacao e aceite. |
| SITE-021 | P1 | Frontend | Criar formulario de contratacao. | Envia para `POST /api/public/contratacoes`. |
| SITE-022 | P1 | Frontend | Criar fluxo de checkout placeholder. | Chama `POST /api/public/checkout/session` e trata retorno/erro. |
| SITE-023 | P1 | Frontend | Criar paginas de sucesso e falha de checkout. | Usuario recebe estado claro apos retorno. |
| SITE-024 | P1 | Frontend | Capturar UTM e referrer. | Payload inclui origem comercial. |
| SITE-025 | P1 | Frontend | Adicionar Open Graph e Twitter Card. | Paginas principais tem metadados completos. |
| SITE-026 | P1 | Frontend | Adicionar dados estruturados basicos. | Organization, SoftwareApplication, Product/Offer e FAQ quando aplicavel. |
| SITE-027 | P1 | Frontend | Criar `robots.txt`. | Staging pode usar noindex e producao pode indexar. |
| SITE-028 | P1 | Frontend | Garantir acessibilidade de formularios. | Labels, foco, erros e teclado funcionam. |
| SITE-029 | P1 | Frontend | Configurar analytics por env. | Eventos page_view, pricing_view, lead_submit, demo_request e checkout_start. |
| SITE-030 | P1 | QA | Rodar build e check. | `npm run check` e `npm run build` passam. |
| SITE-031 | P1 | QA | Testar formulario de lead E2E. | Envio valido, erro de validacao e erro de API funcionam. |
| SITE-032 | P1 | QA | Auditar Lighthouse basico. | Paginas principais batem metas acordadas ou registram pendencias. |
| SITE-033 | P2 | Frontend | Criar blog com Content Collections. | `/blog` e `/blog/[slug]` funcionam. |
| SITE-034 | P2 | Frontend | Criar cases com autorizacao. | `/cases` e `/cases/[slug]` funcionam quando houver conteudo. |
| SITE-035 | P2 | Frontend | Integrar checkout real. | Provedor escolhido redireciona e webhooks sao tratados no backend. |

## Endpoints publicos esperados

| Metodo | Endpoint | Uso |
| --- | --- | --- |
| GET | `/api/public/planos` | Listar planos ativos. |
| POST | `/api/public/leads` | Capturar demo, contato ou interesse comercial. |
| POST | `/api/public/contratacoes` | Criar pre-cadastro de contratacao. |
| POST | `/api/public/checkout/session` | Criar sessao de checkout ou retorno controlado. |
| GET | `/api/public/checkout/status/:sessionId` | Consultar status de checkout quando houver provedor. |

## Regras de negocio

- Site publico nao deve coletar dados de eleitores.
- Formularios devem coletar apenas o minimo necessario.
- Consentimento de contato e aceite legal devem ser registrados no backend.
- Site publico nao processa pagamento diretamente.
- Claims comerciais devem evitar promessa de comprovacao individual de voto.

## Definition of Done

- Paginas publicas obrigatorias existem.
- Formularios enviam dados ao backend.
- SEO tecnico basico esta implementado.
- Build estatico passa.
- Site respeita LGPD e evita coleta sensivel indevida.
