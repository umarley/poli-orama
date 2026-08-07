import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { TenantConfiguration } from '@/modules/tenants/types';

const { getConfiguration, updateConfiguration } = vi.hoisted(() => ({
  getConfiguration: vi.fn(),
  updateConfiguration: vi.fn(),
}));

vi.mock('@/modules/tenants/tenant-service', () => ({
  getTenantConfiguration: getConfiguration,
  updateTenantConfiguration: updateConfiguration,
}));

vi.mock('@/components/feedback/AppToast', () => ({
  AppToast: { success: vi.fn(), error: vi.fn() },
}));

import { TenantTerminologySettingsPage } from './TenantTerminologySettingsPage';

describe('TenantTerminologySettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getConfiguration.mockResolvedValue({
      fuso_horario: 'America/Sao_Paulo',
      percentual_alerta_meta: '80',
      integracoes: {},
      preferencias: { painel_compacto: true },
    });
    updateConfiguration.mockImplementation(async (payload: Partial<TenantConfiguration>) => ({
      fuso_horario: 'America/Sao_Paulo',
      percentual_alerta_meta: '80',
      integracoes: {},
      ...payload,
    }));
  });

  it('salva Frentes sem remover outras preferências do tenant', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <TenantTerminologySettingsPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Como o sistema deve chamar Comunidades?')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText('Frentes'));
    fireEvent.click(screen.getByRole('button', { name: 'Salvar nomenclatura' }));

    await waitFor(() =>
      expect(updateConfiguration).toHaveBeenCalledWith({
        preferencias: {
          painel_compacto: true,
          nomenclatura_comunidades: 'frentes',
        },
      }),
    );
  });
});
