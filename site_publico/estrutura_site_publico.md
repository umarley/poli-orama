# Estrutura do Site Publico (`site_publico`)

Este documento define a estrutura funcional, tecnica e organizacional do projeto `site_publico`, responsavel pelo site publico da plataforma SaaS de inteligencia politica e gestao de campanhas eleitorais.

O projeto deve ficar em:

```text
app_saas/site_publico/
```

O diretorio `site_publico` e independente do painel autenticado (`frontend_core`). Ele atende visitantes, leads, compradores e mecanismos de busca. O painel autenticado continua concentrado no produto operacional usado por campanhas, candidatos e equipes.

## 1. Objetivo

O `site_publico` sera o frontend publico da plataforma, construido com Astro + React para entregar paginas rapidas, indexaveis e preparadas para SEO no Google.

Principais objetivos:

- Apresentar a plataforma, sua proposta de valor e seus modulos.
- Publicar conteudo institucional e comercial.
- Exibir planos de assinatura e recursos incluidos em cada plano.
- Capturar leads para demonstracao, contato comercial e lista de espera.
- Conduzir usuarios ao fluxo de contratacao e pagamento.
- Redirecionar clientes existentes para o painel SaaS.
- Manter paginas legais obrigatorias, como termos de uso, politica de privacidade e LGPD.
- Suportar estrategias de SEO com paginas estaticas, metadados completos, sitemap e dados estruturados.

Fora do escopo do `site_publico`:

- Operacao autenticada da campanha.
- Cadastro e gestao de eleitores.
- Dashboards internos.
- Upload de bases eleitorais.
- Modulos operacionais como agenda, demandas, territorio, metas e modo eleicao dentro da area logada.

Essas funcionalidades pertencem ao `frontend_core` e ao `backend_core`.

## 2. Papel Na Arquitetura Geral

```text
app_saas/
|-- backend_core/         # API principal, autenticacao, tenants, planos e regras de negocio
|-- backend_jobs_celery/  # Jobs, filas, ETL e processamentos assincronos
|-- database/             # Scripts, migracoes e modelos do banco
|-- frontend_core/        # Painel autenticado do SaaS
|-- site_publico/         # Site institucional, SEO, planos e contratacao
`-- specs/                # Especificacoes complementares
```

O `site_publico` se comunica com o backend apenas por APIs publicas e endpoints de checkout. Ele nao deve acessar diretamente o banco de dados.

Integracoes esperadas:

- `backend_core`: planos, leads, pre-cadastro, criacao de sessao de checkout e redirecionamento para onboarding.
- Provedor de pagamento: checkout hospedado ou SDK publico, sem trafegar dados sensiveis de cartao pelo frontend.
- Servico de e-mail/transacional: envio de confirmacoes, notificacoes comerciais e mensagens de onboarding, sempre acionado pelo backend.
- Analytics: medicao de visitas, conversoes, funil de compra e origem de campanhas.

## 3. Stack Tecnica

Stack base:

- Astro como framework principal.
- React para componentes interativos.
- TypeScript para tipagem.
- CSS global e componentes estilizados conforme padrao visual do projeto.
- Markdown/MDX para conteudo editorial e paginas com foco em SEO.
- Build estatico como estrategia inicial.

Justificativa:

- Astro gera HTML estatico por padrao, favorecendo SEO, performance e indexacao.
- React deve ser usado como "ilha interativa" apenas onde houver estado ou interacao real.
- Paginas institucionais, conteudo comercial, blog e termos devem ser renderizados como HTML estatico sempre que possivel.
- O checkout, comparador de planos, formularios e calculadoras podem usar React.

Dependencias sugeridas:

- `@astrojs/react`: suporte a componentes React.
- `@astrojs/sitemap`: geracao automatica de sitemap.
- `astro-seo` ou componente SEO proprio: padronizacao de metadados.
- `zod`: validacao de formularios e contratos de dados.
- `react-hook-form`: formularios interativos.
- `lucide-react`: icones de interface.
- `date-fns`: formatacao de datas quando necessario.
- Provedor de analytics definido por configuracao.

Evitar no MVP:

- Estado global complexo.
- Renderizacao client-side para paginas inteiras.
- CMS externo obrigatorio.
- Dependencia de APIs privadas para renderizar conteudo publico basico.

## 4. Estrutura De Diretorios

Estrutura recomendada:

```text
app_saas/site_publico/
|-- astro.config.mjs
|-- package.json
|-- tsconfig.json
|-- README.md
|-- .env.example
|-- public/
|   |-- favicon.svg
|   |-- robots.txt
|   |-- images/
|   |   |-- marca/
|   |   |-- social/
|   |   |-- screenshots/
|   |   `-- ilustracoes/
|   `-- fonts/
|-- src/
|   |-- assets/
|   |   |-- images/
|   |   `-- icons/
|   |-- components/
|   |   |-- common/
|   |   |-- forms/
|   |   |-- marketing/
|   |   |-- pricing/
|   |   |-- seo/
|   |   `-- ui/
|   |-- content/
|   |   |-- blog/
|   |   |-- cases/
|   |   |-- legal/
|   |   `-- config.ts
|   |-- data/
|   |   |-- navegacao.ts
|   |   |-- planos.ts
|   |   |-- recursos.ts
|   |   |-- faq.ts
|   |   `-- seo.ts
|   |-- integrations/
|   |   |-- analytics.ts
|   |   |-- checkout.ts
|   |   `-- crm.ts
|   |-- layouts/
|   |   |-- BaseLayout.astro
|   |   |-- MarketingLayout.astro
|   |   |-- BlogLayout.astro
|   |   `-- LegalLayout.astro
|   |-- pages/
|   |   |-- index.astro
|   |   |-- plataforma.astro
|   |   |-- planos.astro
|   |   |-- contratar.astro
|   |   |-- checkout/
|   |   |   |-- index.astro
|   |   |   |-- sucesso.astro
|   |   |   `-- falha.astro
|   |   |-- demo.astro
|   |   |-- contato.astro
|   |   |-- recursos/
|   |   |   |-- cadastro-eleitoral.astro
|   |   |   |-- territorio-mapas.astro
|   |   |   |-- metas-liderancas.astro
|   |   |   |-- agenda-demandas.astro
|   |   |   |-- comunicacao.astro
|   |   |   `-- modo-eleicao.astro
|   |   |-- blog/
|   |   |   |-- index.astro
|   |   |   `-- [slug].astro
|   |   |-- cases/
|   |   |   |-- index.astro
|   |   |   `-- [slug].astro
|   |   |-- politica-de-privacidade.astro
|   |   |-- termos-de-uso.astro
|   |   |-- lgpd.astro
|   |   `-- 404.astro
|   |-- scripts/
|   |   `-- structured-data.ts
|   |-- styles/
|   |   |-- global.css
|   |   |-- tokens.css
|   |   `-- utilities.css
|   |-- types/
|   |   |-- lead.ts
|   |   |-- plano.ts
|   |   `-- seo.ts
|   `-- utils/
|       |-- env.ts
|       |-- formatters.ts
|       |-- routes.ts
|       `-- validators.ts
`-- tests/
    |-- e2e/
    `-- unit/
```

## 5. Convencoes De Implementacao

Convencoes gerais:

- Usar nomes de arquivos em `kebab-case` para paginas e componentes Astro.
- Usar `PascalCase` para componentes React.
- Usar `camelCase` para variaveis e funcoes TypeScript.
- Usar `snake_case` apenas quando o dado vier do backend ou representar coluna/tabela.
- Centralizar rotas em `src/utils/routes.ts`.
- Centralizar textos repetidos de navegacao e rodape em `src/data/navegacao.ts`.
- Centralizar planos comerciais em `src/data/planos.ts` quando forem estaticos no MVP.
- Migrar planos para API publica quando o backend de billing estiver pronto.

Uso de Astro:

- Paginas estaticas devem ser `.astro`.
- Layouts globais devem ficar em `src/layouts`.
- Componentes sem estado devem ser Astro por padrao.
- Componentes React devem ser carregados com diretivas `client:*` apenas quando necessario.

Uso de React:

- Formularios de lead, demo e checkout.
- Seletor de ciclo mensal/anual.
- Comparador de planos.
- FAQ expansivel.
- Calculadoras comerciais.
- Componentes que dependem de estado local, validacao ou chamadas de API.

Evitar:

- Transformar o site inteiro em SPA.
- Buscar dados criticos de SEO somente no cliente.
- Repetir metadados manualmente em cada pagina sem componente padrao.
- Deixar textos comerciais espalhados em componentes sem estrutura.

## 6. Rotas Publicas

Rotas obrigatorias do MVP:

| Rota | Tipo | Objetivo |
| ---- | ---- | -------- |
| `/` | Institucional | Primeira pagina de venda, proposta de valor, principais recursos e chamadas para demo/planos. |
| `/plataforma` | Institucional | Explicacao completa da plataforma e seus modulos. |
| `/planos` | Comercial | Comparacao de planos, limites, beneficios e CTA de contratacao. |
| `/contratar` | Comercial | Captura dos dados iniciais para iniciar contratacao. |
| `/checkout` | Comercial | Inicio ou redirecionamento para sessao de pagamento. |
| `/checkout/sucesso` | Comercial | Confirmacao de pagamento ou solicitacao recebida. |
| `/checkout/falha` | Comercial | Erro, cancelamento ou pagamento recusado. |
| `/demo` | Comercial | Solicitacao de demonstracao. |
| `/contato` | Comercial | Contato institucional e comercial. |
| `/politica-de-privacidade` | Legal | Politica de privacidade e tratamento de dados. |
| `/termos-de-uso` | Legal | Condicoes de uso da plataforma. |
| `/lgpd` | Legal | Explicacao de bases legais, direitos do titular e canal LGPD. |
| `/404` | Sistema | Pagina de erro nao encontrado. |

Rotas de recursos:

| Rota | Objetivo |
| ---- | -------- |
| `/recursos/cadastro-eleitoral` | Explicar cadastros, liderancas, nucleos familiares e duplicidade. |
| `/recursos/territorio-mapas` | Explicar georreferenciamento, bairros, zonas, secoes e mapas. |
| `/recursos/metas-liderancas` | Explicar metas, ranking de liderancas e alertas. |
| `/recursos/agenda-demandas` | Explicar agenda politica, eventos, demandas e atendimentos. |
| `/recursos/comunicacao` | Explicar interacoes e comunicacao com base cadastrada. |
| `/recursos/modo-eleicao` | Explicar acompanhamento operacional do dia da votacao. |

Rotas editoriais:

| Rota | Objetivo |
| ---- | -------- |
| `/blog` | Listar conteudos educativos e SEO. |
| `/blog/[slug]` | Publicar artigos indexaveis. |
| `/cases` | Listar estudos de caso, quando existirem. |
| `/cases/[slug]` | Detalhar um caso com prova social autorizada. |

Rotas auxiliares:

| Rota | Objetivo |
| ---- | -------- |
| `/login` | Redirecionar para o `frontend_core` autenticado. |
| `/obrigado` | Confirmar envio de formulario quando nao houver checkout imediato. |

## 7. Conteudo Por Pagina

### Home (`/`)

Deve conter:

- Proposta de valor clara.
- Publico-alvo: candidatos, coordenadores, equipes de campanha e consultorias politicas.
- Beneficios principais.
- Resumo dos modulos.
- CTA para demonstracao e planos.
- Sinais de confianca: seguranca, LGPD, organizacao de dados e suporte.
- FAQ curta.
- Links para paginas legais.

### Plataforma (`/plataforma`)

Deve conter:

- Visao geral do produto.
- Organizacao por modulos.
- Como os dados fluem entre cadastro, territorio, metas, agenda, demandas e modo eleicao.
- Diferenca entre inteligencia politica e planilhas dispersas.
- Chamada para demo.

### Planos (`/planos`)

Deve conter:

- Tabela comparativa.
- Ciclo mensal e anual, se aplicavel.
- Limites comerciais.
- Recursos incluidos.
- Perguntas frequentes comerciais.
- CTA por plano.
- Aviso de que precos, limites e disponibilidade podem depender da configuracao comercial vigente.

### Contratar (`/contratar`)

Deve conter:

- Selecao de plano.
- Dados do responsavel.
- Dados basicos da campanha/organizacao.
- Aceite dos termos.
- Captura de UTM.
- Inicio de checkout ou envio para atendimento comercial.

### Demo (`/demo`)

Deve conter:

- Formulario enxuto.
- Perfil do interessado.
- Tamanho estimado da equipe.
- Cidade/UF de atuacao.
- Melhor canal de contato.
- Consentimento para contato.

### Blog (`/blog`)

Deve conter:

- Artigos educativos sobre organizacao de campanha, gestao territorial, liderancas, metas e dados.
- Conteudo orientado a busca organica.
- Categorias, tags e pagina de artigo com dados estruturados.

## 8. Modelo De Planos

O site deve refletir a entidade `plano_assinatura` definida na documentacao do banco. No MVP, os planos podem estar em `src/data/planos.ts`. Quando o backend estiver pronto, o site deve consumir uma API publica para garantir que os valores exibidos sejam os mesmos usados no checkout.

Modelo sugerido:

```ts
export type PlanoAssinatura = {
  slug: string;
  nome: string;
  descricao: string;
  publicoAlvo: string;
  destaque?: boolean;
  ativo: boolean;
  ordem: number;
  precoMensal?: number;
  precoAnual?: number;
  moeda: 'BRL';
  cicloPadrao: 'mensal' | 'anual';
  limiteUsuarios?: number;
  limiteEleitores?: number;
  limiteLiderancas?: number;
  limiteCampanhas?: number;
  recursos: string[];
  recursosNaoIncluidos?: string[];
  ctaLabel: string;
  ctaHref: string;
};
```

Sugestao de segmentacao comercial:

| Plano | Perfil | Caracteristica |
| ----- | ------ | -------------- |
| `essencial` | Campanhas pequenas ou pre-campanhas | Cadastro, liderancas e operacao basica. |
| `profissional` | Campanhas em crescimento | Metas, territorio, demandas, agenda e relatorios. |
| `operacao` | Campanhas maiores ou consultorias | Recursos avancados, modo eleicao, mais usuarios e suporte prioritario. |
| `enterprise` | Operacoes customizadas | Contrato sob demanda, integracoes e limites negociados. |

Os nomes comerciais podem mudar, mas a estrutura precisa permitir:

- Plano ativo/inativo.
- Destaque do plano recomendado.
- Diferenca entre preco mensal e anual.
- Limites por recurso.
- Recursos habilitados.
- CTA para checkout automatico ou contato comercial.

## 9. Contratos De Dados Publicos

### Lead Comercial

Formulario usado em `/contato`, `/demo` e CTAs comerciais.

```ts
export type LeadComercialPayload = {
  nome: string;
  email: string;
  telefone?: string;
  organizacao?: string;
  cargo?: string;
  cidade?: string;
  uf?: string;
  interesse: 'demo' | 'planos' | 'contato' | 'checkout_abandonado';
  mensagem?: string;
  planoSlug?: string;
  origem?: {
    utmSource?: string;
    utmMedium?: string;
    utmCampaign?: string;
    utmTerm?: string;
    utmContent?: string;
    referrer?: string;
    landingPage?: string;
  };
  consentimentoContato: boolean;
};
```

Endpoint sugerido:

```text
POST /api/public/leads
```

### Pre-Cadastro De Contratacao

Formulario usado em `/contratar`.

```ts
export type ContratacaoPayload = {
  planoSlug: string;
  ciclo: 'mensal' | 'anual';
  responsavel: {
    nome: string;
    email: string;
    telefone: string;
    documento?: string;
  };
  organizacao: {
    nome: string;
    tipo: 'candidato' | 'partido' | 'consultoria' | 'mandato' | 'outro';
    cidade?: string;
    uf?: string;
  };
  origem?: LeadComercialPayload['origem'];
  aceiteTermos: boolean;
  aceitePrivacidade: boolean;
};
```

Endpoint sugerido:

```text
POST /api/public/contratacoes
```

### Sessao De Checkout

O frontend nunca deve processar pagamento diretamente. Ele solicita ao backend a criacao de uma sessao e redireciona o usuario para o provedor de pagamento ou checkout hospedado.

```ts
export type CheckoutSessionRequest = {
  contratacaoId: string;
  planoSlug: string;
  ciclo: 'mensal' | 'anual';
  cupom?: string;
};

export type CheckoutSessionResponse = {
  checkoutUrl: string;
  sessionId: string;
  expiresAt: string;
};
```

Endpoint sugerido:

```text
POST /api/public/checkout/session
```

Regras:

- Webhooks de pagamento pertencem ao backend.
- O frontend deve tratar sucesso, falha, cancelamento e expiracao.
- A criacao de tenant deve ocorrer somente apos confirmacao confiavel do pagamento ou aprovacao comercial.
- Chamadas de checkout devem ser idempotentes no backend.

## 10. SEO

O projeto deve ser construido com SEO como requisito central.

Requisitos por pagina:

- `title` unico.
- `description` unica.
- URL canonica.
- Open Graph.
- Twitter Card.
- H1 unico e coerente.
- Hierarquia correta de headings.
- Imagens com `alt`.
- Conteudo principal renderizado no HTML inicial.
- Links internos entre paginas relacionadas.
- Schema.org quando aplicavel.

Arquivos e configuracoes obrigatorias:

- `sitemap.xml` gerado no build.
- `robots.txt` em `public/robots.txt`.
- Pagina `404`.
- URLs amigaveis.
- Redirecionamentos controlados quando houver mudanca de slug.
- `canonical` usando `PUBLIC_SITE_URL`.

Dados estruturados recomendados:

- `Organization`: dados da empresa/plataforma.
- `SoftwareApplication`: descrever a plataforma SaaS.
- `Product`: planos e oferta comercial quando aplicavel.
- `Offer`: preco, moeda e disponibilidade dos planos.
- `FAQPage`: perguntas frequentes de paginas comerciais.
- `BreadcrumbList`: paginas internas.
- `Article`: posts do blog.

Componente SEO padrao:

```ts
export type SeoConfig = {
  title: string;
  description: string;
  canonicalPath: string;
  noindex?: boolean;
  image?: string;
  type?: 'website' | 'article';
  structuredData?: Record<string, unknown>[];
};
```

Palavras-chave e temas de conteudo:

- sistema para campanha eleitoral.
- gestao de campanha eleitoral.
- CRM politico.
- inteligencia politica.
- gestao de liderancas.
- mapa eleitoral.
- metas de votos.
- organizacao de base eleitoral.
- software para campanha politica.
- plataforma para coordenacao de campanha.

As palavras-chave devem orientar o conteudo, mas o texto deve priorizar clareza, conformidade legal e utilidade real.

## 11. Conteudo Editorial E CMS

Para o MVP, o conteudo deve ser versionado no repositorio usando Content Collections do Astro.

Colecoes sugeridas:

```text
src/content/blog/
src/content/cases/
src/content/legal/
```

Frontmatter sugerido para blog:

```yaml
---
title: "Como organizar liderancas em uma campanha eleitoral"
description: "Guia pratico para estruturar liderancas, territorios e metas com apoio de tecnologia."
publishDate: "2026-06-24"
updatedDate: "2026-06-24"
author: "Equipe"
category: "Gestao de campanha"
tags:
  - campanha eleitoral
  - liderancas
  - metas
seo:
  noindex: false
---
```

Regras:

- Todo artigo deve ter `title`, `description`, `publishDate`, `category` e `tags`.
- O slug deve ser estavel.
- Conteudos legais devem ter data de vigencia e versao.
- Estudos de caso so devem ser publicados com autorizacao explicita.
- Conteudos que envolvam legislacao eleitoral devem ser revisados antes de publicacao.

## 12. LGPD, Privacidade E Conformidade

O site publico deve evitar coleta desnecessaria de dados.

Regras:

- Coletar apenas dados necessarios para contato, demo ou contratacao.
- Exibir aceite de politica de privacidade em formularios comerciais.
- Registrar consentimento no backend.
- Informar finalidade do contato.
- Nao coletar dados sensiveis de eleitores no site publico.
- Nao permitir upload de planilhas ou bases eleitorais fora da area autenticada.
- Nao prometer comprovacao individual de voto.
- Usar linguagem compativel com finalidade operacional e legal da plataforma.
- Disponibilizar canal para solicitacoes LGPD.

Cookies e tracking:

- Analytics basico pode ser carregado com consentimento conforme decisao juridica do projeto.
- Pixels de marketing devem respeitar consentimento e politica de privacidade.
- Parametros UTM podem ser armazenados temporariamente para atribuicao comercial.

Paginas legais obrigatorias:

- `/politica-de-privacidade`
- `/termos-de-uso`
- `/lgpd`

## 13. Analytics E Conversao

Eventos recomendados:

| Evento | Quando disparar |
| ------ | --------------- |
| `page_view` | Visualizacao de pagina. |
| `pricing_view` | Visualizacao da pagina de planos. |
| `plan_select` | Clique em CTA de plano. |
| `lead_submit` | Envio de formulario comercial. |
| `demo_request` | Solicitacao de demo. |
| `checkout_start` | Inicio de checkout. |
| `checkout_success` | Retorno de pagamento aprovado ou solicitacao recebida. |
| `checkout_failure` | Retorno de falha/cancelamento. |
| `login_click` | Clique para acessar o painel. |

Dados minimos por evento:

- `event_name`
- `page_path`
- `plan_slug`, quando aplicavel.
- `utm_source`, `utm_medium`, `utm_campaign`, quando existirem.
- `timestamp`

Nao enviar para analytics:

- CPF.
- Documento pessoal.
- Telefone completo, salvo se a ferramenta tiver base legal e contrato adequado.
- Dados de eleitores.
- Informacoes politicas sensiveis de pessoas fisicas.

## 14. Variaveis De Ambiente

Arquivo `.env.example` sugerido:

```env
PUBLIC_SITE_URL=https://www.exemplo.com.br
PUBLIC_APP_LOGIN_URL=https://app.exemplo.com.br/login
PUBLIC_API_BASE_URL=https://api.exemplo.com.br
PUBLIC_ANALYTICS_PROVIDER=none
PUBLIC_ANALYTICS_ID=
PUBLIC_CHECKOUT_PROVIDER=external
PUBLIC_RECAPTCHA_SITE_KEY=
PUBLIC_SUPPORT_EMAIL=contato@exemplo.com.br
PUBLIC_SUPPORT_WHATSAPP=
```

Regras:

- Somente variaveis prefixadas com `PUBLIC_` podem ser expostas ao navegador.
- Segredos de API, tokens privados e chaves secretas pertencem ao backend.
- URLs devem variar por ambiente: local, staging e producao.

## 15. Formularios

Formularios obrigatorios:

- Lead comercial.
- Solicitacao de demo.
- Contratacao.
- Contato institucional.
- Newsletter, se houver estrategia de conteudo.

Requisitos:

- Validacao client-side com mensagens claras.
- Validacao server-side obrigatoria no backend.
- Protecao anti-spam.
- Captura de origem UTM.
- Estado de carregamento.
- Estado de sucesso.
- Estado de erro recuperavel.
- Acessibilidade em labels, foco e mensagens.

Campos sensiveis devem ser minimizados. Documentos pessoais so devem ser solicitados quando forem realmente necessarios para contratacao.

## 16. Design E Experiencia

Diretrizes:

- Aparencia institucional, profissional e objetiva.
- Priorizar clareza comercial, leitura rapida e prova de valor.
- Evitar visual excessivamente decorativo.
- Usar screenshots ou representacoes reais do produto quando disponiveis.
- Usar componentes consistentes entre home, recursos e planos.
- Garantir boa experiencia mobile.
- CTAs devem ser claros: "Agendar demo", "Ver planos", "Contratar", "Falar com consultor".

Componentes principais:

- Header com navegacao e CTA.
- Footer com links legais e contato.
- Hero da home.
- Grade de recursos.
- Tabela de planos.
- Comparador de recursos.
- FAQ.
- Formulario de lead.
- Cards de artigos.
- Banner de consentimento de cookies, se adotado.
- Breadcrumbs em paginas internas.

## 17. Performance

Metas:

- Lighthouse Performance >= 90 em paginas principais.
- Lighthouse SEO >= 95.
- Lighthouse Accessibility >= 90.
- Largest Contentful Paint abaixo de 2,5s em conexoes comuns.
- Evitar JavaScript desnecessario em paginas estaticas.

Praticas obrigatorias:

- Imagens otimizadas.
- Carregamento tardio de imagens abaixo da dobra.
- CSS enxuto.
- Fontes locais ou carregadas com estrategia eficiente.
- Componentes React hidratados apenas quando necessario.
- Build estatico para conteudo publico.

## 18. Acessibilidade

Requisitos:

- Navegacao por teclado.
- Contraste adequado.
- Labels em formularios.
- Mensagens de erro associadas aos campos.
- Foco visivel.
- Texto alternativo em imagens informativas.
- Evitar depender apenas de cor para comunicar estado.
- Headings em ordem semantica.

## 19. Seguranca

Regras:

- Usar HTTPS em producao.
- Nao expor segredos no frontend.
- Validar payloads no backend.
- Proteger formularios contra spam e abuso.
- Configurar Content Security Policy no ambiente de deploy quando possivel.
- Nao armazenar dados sensiveis em `localStorage`.
- Nao aceitar HTML arbitrario vindo de formularios.
- Sanitizar conteudo editorial se houver fonte externa.

## 20. Integracao Com Backend

Endpoints publicos sugeridos:

```text
GET  /api/public/planos
POST /api/public/leads
POST /api/public/contratacoes
POST /api/public/checkout/session
GET  /api/public/checkout/status/:sessionId
```

Responsabilidades do backend:

- Validar dados recebidos.
- Registrar leads e consentimentos.
- Consultar planos ativos.
- Criar contratacao pendente.
- Criar sessao de checkout.
- Processar webhooks de pagamento.
- Ativar assinatura.
- Criar tenant inicial apos confirmacao.
- Enviar e-mails transacionais.
- Registrar logs de auditoria comercial.

Responsabilidades do site publico:

- Renderizar conteudo e planos.
- Capturar dados do usuario.
- Validar formato basico dos campos.
- Enviar payloads para APIs publicas.
- Redirecionar para checkout.
- Exibir estados de sucesso/falha.
- Preservar parametros de atribuicao.

## 21. Deploy

Estrategia inicial recomendada:

- Build estatico do Astro.
- Publicacao do diretorio `dist/`.
- Hospedagem em CDN, Nginx, Cloudflare Pages, Vercel, Netlify ou infraestrutura propria.
- Dominio publico separado do app autenticado.

Exemplo:

```text
www.plataforma.com.br        -> site_publico
app.plataforma.com.br        -> frontend_core
api.plataforma.com.br        -> backend_core
```

Comandos esperados:

```bash
npm install
npm run dev
npm run check
npm run build
npm run preview
```

Ambientes:

| Ambiente | Uso |
| -------- | --- |
| Local | Desenvolvimento. |
| Staging | Validacao comercial, SEO, checkout sandbox e QA. |
| Producao | Site publico indexavel. |

Em staging, usar `noindex` para evitar indexacao indevida.

## 22. Testes E Qualidade

Testes recomendados:

- Build do Astro.
- Validacao TypeScript.
- Testes unitarios de validadores e formatadores.
- Testes E2E do fluxo de lead.
- Testes E2E do fluxo de contratacao ate redirecionamento de checkout.
- Validacao de sitemap.
- Validacao de metadados.
- Validacao de links internos.
- Auditoria Lighthouse.

Criterios minimos antes de publicar:

- `npm run check` sem erros.
- `npm run build` sem erros.
- Nenhuma pagina principal com `title` ou `description` ausente.
- `robots.txt` revisado.
- `sitemap.xml` gerado.
- Formularios testados em sucesso e erro.
- Checkout testado em sandbox, quando implementado.
- Paginas legais disponiveis.

## 23. Roadmap De Implementacao

### Fase 1 - Base Institucional

- Criar projeto Astro + React.
- Configurar TypeScript, estilos globais e layouts.
- Implementar home, plataforma, recursos, planos, contato, demo e paginas legais.
- Configurar SEO base, sitemap e robots.
- Implementar formularios com envio para endpoint mockado ou backend.

### Fase 2 - Funil Comercial

- Integrar planos reais.
- Implementar contratacao.
- Criar fluxo de checkout.
- Capturar UTM.
- Registrar eventos de conversao.
- Criar paginas de sucesso e falha.

### Fase 3 - Conteudo E SEO

- Implementar blog com Content Collections.
- Criar paginas de recursos focadas em palavras-chave.
- Adicionar dados estruturados.
- Melhorar links internos.
- Criar calendario editorial.

### Fase 4 - Otimizacao

- Rodar auditoria Lighthouse.
- Ajustar performance.
- Implementar experimentos de conversao.
- Integrar CMS externo, se houver necessidade operacional.
- Ampliar automacoes comerciais.

## 24. Checklist De Entrega Do MVP

- [ ] Projeto Astro criado em `app_saas/site_publico`.
- [ ] React configurado para componentes interativos.
- [ ] Layout base implementado.
- [ ] Home publicada.
- [ ] Pagina da plataforma publicada.
- [ ] Pagina de planos publicada.
- [ ] Paginas de recursos publicadas.
- [ ] Formularios de demo e contato implementados.
- [ ] Pagina de contratar implementada.
- [ ] Paginas legais implementadas.
- [ ] SEO padrao aplicado em todas as paginas.
- [ ] Sitemap configurado.
- [ ] Robots configurado.
- [ ] Dados estruturados basicos adicionados.
- [ ] Analytics configurado conforme decisao do projeto.
- [ ] UTM capturada nos formularios.
- [ ] Build validado.
- [ ] Staging validado com `noindex`.
- [ ] Producao publicada com dominio final.

## 25. Decisoes Arquiteturais

Decisoes iniciais:

- O `site_publico` sera um projeto separado do `frontend_core`.
- Astro sera o framework principal.
- React sera usado somente para interacoes necessarias.
- SEO sera tratado como requisito de arquitetura, nao como ajuste posterior.
- Planos comerciais devem ser representados de forma compativel com `plano_assinatura`.
- O frontend nao processara pagamento diretamente.
- Webhooks e ativacao de assinatura pertencem ao backend.
- Paginas legais fazem parte do MVP.
- Conteudo editorial inicial ficara versionado no repositorio.

Pontos pendentes de definicao:

- Nome comercial final da plataforma.
- Identidade visual final.
- Provedor de pagamento.
- Provedor de analytics.
- Politica de precos e limites por plano.
- Regras juridicas finais para textos legais, cookies e claims comerciais.
- Dominio final de producao.
