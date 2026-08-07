import { canViewNavigationItem, getNavigationLabel, navigationItems } from '@/app/navigation';

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

  it('usa o item mais específico em rotas internas de cadastro', () => {
    expect(getNavigationLabel('/cadastro/segmentacao')).toBe('Tags e comunidades');
    expect(getNavigationLabel('/cadastro/indicacoes')).toBe('Rede de indicações');
    expect(getNavigationLabel('/cadastro/duplicidades')).toBe('Duplicidades');
  });
});
