import { canViewNavigationItem, navigationItems } from '@/app/navigation';

describe('navegação por permissão', () => {
  it('oculta módulos sem permissão efetiva', () => {
    const visible = navigationItems
      .filter((item) => canViewNavigationItem(item, ['cadastro.visualizar'], ['telefonista']))
      .map((item) => item.key);

    expect(visible).toContain('/cadastro');
    expect(visible).not.toContain('/metas');
    expect(visible).not.toContain('/admin/tenants');
  });

  it('exibe administração SaaS somente ao perfil correspondente', () => {
    const tenants = navigationItems.find((item) => item.key === '/admin/tenants');
    expect(tenants).toBeDefined();
    expect(canViewNavigationItem(tenants!, [], ['gestor_saas'])).toBe(true);
    expect(canViewNavigationItem(tenants!, [], ['gestor'])).toBe(false);
  });
});
