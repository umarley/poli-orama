# Frontend — Poliorama

Fundação React + Vite do SaaS de campanha eleitoral, implementada a partir da
`SPEC-01-fundacao-tecnica-arquitetura.md`.

## Requisitos

- Node.js 20.19 ou superior
- pnpm 11

O Node.js 16 não é suportado pelas versões atuais do Vite.

## Execução

```bash
cp .env.example .env
pnpm install
pnpm dev
```

A aplicação estará disponível em `http://127.0.0.1:5173`.

O login exige o slug da campanha, e-mail e senha cadastrados no backend. A sessão usa
access token curto e refresh token rotativo; respostas 401 tentam uma única renovação
antes de encerrar a sessão.

## Comandos

```bash
pnpm dev          # servidor de desenvolvimento
pnpm build        # typecheck e build de produção
pnpm lint         # análise estática
pnpm format       # formatação do projeto
pnpm format:check # valida a formatação
pnpm test         # testes unitários
pnpm test:e2e     # testes Playwright
pnpm preview      # serve o build localmente
```

Antes do primeiro teste E2E, instale o navegador do Playwright:

```bash
pnpm exec playwright install chromium
```

## Estrutura

```text
src/
  app/          # providers, rotas e navegação
  components/   # componentes reutilizáveis
  config/       # configuração por ambiente
  layouts/      # shell autenticado
  modules/      # tipos, serviços e regras por domínio
  pages/        # composição das telas
  services/     # infraestrutura HTTP
  stores/       # estado global leve
  styles/       # tokens e estilos globais
  test/         # configuração de testes
  types/        # contratos compartilhados
```

## Padrões

- Imports internos usam o alias `@/`.
- Cores, tipografia, raios e dimensões básicas estão centralizados em
  `src/styles/theme.ts`.
- O cliente Axios injeta `Authorization` e `X-Campaign-ID` e normaliza
  erros no formato `{ code, message, details }`.
- A sessão mantém usuário, tenant, permissões, access token e refresh token com Zustand.
- Menus e rotas são filtrados pela permissão efetiva retornada pela API.
- Gestores podem configurar MFA TOTP e todos os usuários podem consultar e revogar
  sessões em **Segurança e acessos**.
- Dados assíncronos e invalidação de cache usam TanStack Query.
- Rotas autenticadas ficam sob `AuthenticatedLayout`.
- Novos domínios devem manter contratos e serviços em `src/modules/<dominio>`.

## Variáveis

| Variável               | Descrição                                   | Padrão                         |
| ---------------------- | ------------------------------------------- | ------------------------------ |
| `VITE_API_URL`         | URL base da API                             | `http://localhost:8000/api/v1` |
| `VITE_APP_NAME`        | Nome exibido pela aplicação                 | `Poliorama`              |
| `VITE_ENABLE_DEVTOOLS` | Reserva para ferramentas de desenvolvimento | `false`                        |
