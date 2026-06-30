import { expect, test } from '@playwright/test';

test('autentica na API e navega apenas pelos módulos permitidos', async ({ page }) => {
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'access-token-test',
        refresh_token: 'refresh-token-test',
        token_type: 'bearer',
        expires_in: 1800,
        usuario: {
          id: 1,
          uuid_publico: '00000000-0000-0000-0000-000000000001',
          tenant_id: 1,
          nome: 'Marina Costa',
          email: 'gestor@campanha.com.br',
          status: 'ativo',
          deve_alterar_senha: false,
          mfa_habilitado: false,
          criado_em: '2026-06-30T00:00:00Z',
          atualizado_em: '2026-06-30T00:00:00Z',
          perfis: [
            {
              id: 1,
              nome: 'Gestor',
              codigo: 'gestor',
              nivel: 1,
              permissoes: [],
            },
          ],
          permissoes: ['dashboard.visualizar', 'cadastro.visualizar', 'usuarios.visualizar'],
          acessos_territoriais: [],
        },
      }),
    });
  });
  await page.route('**/api/v1/me/tenant', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        uuid_publico: '00000000-0000-0000-0000-000000000001',
        nome: 'Ricardo Almeida',
        slug: 'ricardo-almeida',
        tem_mandato: false,
        status: 'ativo',
        criado_em: '2026-06-30T00:00:00Z',
        atualizado_em: '2026-06-30T00:00:00Z',
      }),
    });
  });
  await page.route('**/api/v1/auth/sessions', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 1,
          dispositivo: 'Chrome no Windows',
          user_agent: 'Playwright',
          ip_origem: '127.0.0.1',
          criado_em: '2026-06-30T10:00:00Z',
          ultimo_uso_em: '2026-06-30T12:00:00Z',
          expira_em: '2026-07-07T10:00:00Z',
          revogada_em: null,
          atual: true,
          status: 'ativa',
        },
      ]),
    });
  });

  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Acesse sua campanha' })).toBeVisible();
  await page.getByLabel('Campanha').fill('ricardo-almeida');
  await page.getByLabel('E-mail').fill('gestor@campanha.com.br');
  await page.getByLabel('Senha').fill('Senha-segura-123!');
  await page.getByRole('button', { name: 'Entrar' }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'Painel de controle' })).toBeVisible();

  if ((page.viewportSize()?.width ?? 1280) < 768) {
    await page.getByRole('button', { name: 'Abrir menu' }).click();
  }

  await expect(page.getByRole('menuitem', { name: 'Pessoas e eleitores' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Usuários e perfis' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: 'Metas e votos' })).toHaveCount(0);

  await page.getByRole('menuitem', { name: 'Segurança e acessos' }).click();
  await expect(page.getByRole('heading', { name: 'Segurança e acessos' })).toBeVisible();
  await expect(page.getByText('Chrome no Windows')).toBeVisible();

  if ((page.viewportSize()?.width ?? 1280) < 768) {
    await page.getByRole('button', { name: 'Abrir menu' }).click();
  }
  await page.getByRole('menuitem', { name: 'Pessoas e eleitores' }).click();
  await expect(page.getByRole('heading', { name: 'Pessoas e eleitores' })).toBeVisible();
  await expect(page.getByText('Ana Beatriz Souza')).toBeVisible();
});
