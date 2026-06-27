import { expect, test } from '@playwright/test';

test('abre o login, autentica e navega pelo shell', async ({ page }) => {
  await page.goto('/login');

  await expect(page.getByRole('heading', { name: 'Acesse sua campanha' })).toBeVisible();
  await page.getByLabel('Senha').fill('demo123');
  await page.getByRole('button', { name: 'Entrar' }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole('heading', { name: 'Painel de controle' })).toBeVisible();

  if ((page.viewportSize()?.width ?? 1280) < 768) {
    await page.getByRole('button', { name: 'Abrir menu' }).click();
  }

  await expect(page.getByText('Ricardo Almeida 2026', { exact: true })).toBeVisible();
  await expect(page.getByText('Deputado estadual · Eleições 2026')).toBeVisible();

  await page.getByRole('menuitem', { name: 'Pessoas e eleitores' }).click();
  await expect(page.getByRole('heading', { name: 'Pessoas e eleitores' })).toBeVisible();
  await expect(page.getByText('Ana Beatriz Souza')).toBeVisible();
});
