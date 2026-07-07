import { expect, test } from "@playwright/test";

test("exibe erros de validação acessíveis", async ({ page }) => {
  await page.goto("/demo");
  await page.getByRole("button", { name: "Enviar solicitação" }).click();
  await expect(page.getByText("Informe seu nome.")).toBeVisible();
  await expect(page.getByText("Informe um e-mail válido.")).toBeVisible();
  await expect(page.getByText("Autorize o contato para continuar.")).toBeVisible();
  await expect(page.locator("[name=nome]")).toBeFocused();
});

test("envia um lead válido para a API", async ({ page }) => {
  let payload: Record<string, unknown> | undefined;
  await page.route("**/api/public/leads", async (route) => {
    payload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ id: "00000000-0000-0000-0000-000000000001", status: "recebido" }),
    });
  });
  await page.goto("/demo?utm_source=e2e&utm_campaign=site");
  await page.getByLabel("Nome").fill("Maria Teste");
  await page.getByLabel("E-mail").fill("maria@example.com");
  await page.getByLabel(/Autorizo o uso/).check();
  await page.getByRole("button", { name: "Enviar solicitação" }).click();
  await expect(page.getByRole("status")).toContainText("Solicitação recebida");
  expect(payload).toMatchObject({
    nome: "Maria Teste",
    email: "maria@example.com",
    interesse: "demo",
    consentimento: true,
    origem: { utm_source: "e2e", utm_campaign: "site" },
  });
});

test("mantém o formulário recuperável quando a API falha", async ({ page }) => {
  await page.route("**/api/public/leads", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ message: "Serviço temporariamente indisponível." }),
    }),
  );
  await page.goto("/contato");
  await page.getByLabel("Nome").fill("João Teste");
  await page.getByLabel("E-mail").fill("joao@example.com");
  await page.getByLabel(/Autorizo o uso/).check();
  await page.getByRole("button", { name: "Enviar solicitação" }).click();
  await expect(page.getByRole("alert")).toContainText("Serviço temporariamente indisponível");
  await expect(page.getByLabel("Nome")).toHaveValue("João Teste");
  await expect(page.getByRole("button", { name: "Enviar solicitação" })).toBeEnabled();
});
