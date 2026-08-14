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

import { TenantCadastroSettingsPage } from './TenantCadastroSettingsPage';

describe('TenantCadastroSettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getConfiguration.mockResolvedValue({
      fuso_horario: 'America/Sao_Paulo',
      percentual_alerta_meta: '80',
      integracoes: {},
      preferencias: { nomenclatura_liderancas: 'liderancas' },
    });
    updateConfiguration.mockImplementation(async (payload: Partial<TenantConfiguration>) => ({
      fuso_horario: 'America/Sao_Paulo',
      percentual_alerta_meta: '80',
      integracoes: {},
      ...payload,
    }));
  });

  it('salva os campos obrigatórios sem alterar outras preferências e mantém o nome completo', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <TenantCadastroSettingsPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByRole('button', { name: 'Salvar campos obrigatórios' })).toBeInTheDocument();
    expect(screen.getByLabelText('Nome completo')).toBeDisabled();

    fireEvent.click(screen.getByLabelText('Data de nascimento'));
    fireEvent.click(screen.getByLabelText('CPF'));
    fireEvent.click(screen.getByLabelText('WhatsApp'));
    fireEvent.click(screen.getByRole('button', { name: 'Salvar campos obrigatórios' }));

    await waitFor(() =>
      expect(updateConfiguration).toHaveBeenCalledWith({
        preferencias: {
          nomenclatura_liderancas: 'liderancas',
          formulario_cadastro: {
            nome_completo: true,
            data_nascimento: true,
            sexo: false,
            estado_civil: false,
            documento: { CPF: true, RG: false, CNH: false },
            canal: { WhatsApp: true, Celular: false, Telefone: false, 'E-mail': false },
            titulo_eleitoral: false,
          },
        },
      }),
    );
  });
});
