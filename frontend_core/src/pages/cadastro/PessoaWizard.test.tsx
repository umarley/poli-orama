import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { getConfiguration, searchPeople, createPerson, listStates, listCities } = vi.hoisted(() => ({
  getConfiguration: vi.fn(),
  searchPeople: vi.fn(),
  createPerson: vi.fn(),
  listStates: vi.fn(),
  listCities: vi.fn(),
}));

vi.mock('@/modules/tenants/tenant-service', () => ({
  getTenantConfiguration: getConfiguration,
}));

vi.mock('@/modules/cadastro/pessoas-service', () => ({
  buscarPessoas: searchPeople,
  criarPessoa: createPerson,
}));

vi.mock('@/modules/territorios/territorios-service', () => ({
  listarEstados: listStates,
  listarMunicipios: listCities,
  listarZonas: vi.fn().mockResolvedValue([]),
  listarLocaisVotacao: vi.fn().mockResolvedValue([]),
  listarSecoes: vi.fn().mockResolvedValue([]),
}));

import { PessoaWizard } from './PessoaWizard';

function renderWizard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <PessoaWizard
          open
          tipos={[]}
          liderancas={[]}
          estadosCivis={[{ id: 1, codigo: 'solteiro', nome: 'Solteiro', ordem: 1 }]}
          onClose={() => undefined}
          onCreated={() => undefined}
        />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('PessoaWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    searchPeople.mockResolvedValue([]);
    listStates.mockResolvedValue([]);
    listCities.mockResolvedValue([]);
  });

  it('aplica campos obrigatórios da configuração do tenant no cadastro interno', async () => {
    getConfiguration.mockResolvedValue({
      fuso_horario: 'America/Sao_Paulo',
      percentual_alerta_meta: '80',
      integracoes: {},
      preferencias: {
        formulario_cadastro: {
          nome_completo: true,
          sexo: true,
          documento: { CPF: true, RG: false, CNH: false },
          canal: { WhatsApp: false, Celular: false, Telefone: false, 'E-mail': false },
        },
      },
    });

    renderWizard();

    fireEvent.change(await screen.findByPlaceholderText('Nome da pessoa'), {
      target: { value: 'Maria Silva' },
    });
    await waitFor(() => expect(screen.getByTitle('Sexo')).toHaveClass('ant-form-item-required'));
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));

    expect(await screen.findByText('Selecione o sexo.')).toBeInTheDocument();
    expect(screen.getByText('Dados básicos')).toBeInTheDocument();
  });

  it('permite avançar só com o nome quando os demais campos estão opcionais', async () => {
    getConfiguration.mockResolvedValue({
      fuso_horario: 'America/Sao_Paulo',
      percentual_alerta_meta: '80',
      integracoes: {},
      preferencias: {},
    });

    renderWizard();

    fireEvent.change(await screen.findByPlaceholderText('Nome da pessoa'), {
      target: { value: 'Maria Silva' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Continuar' }));

    await waitFor(() => expect(screen.getByText('Documento')).toBeInTheDocument());
    expect(screen.queryByText('Selecione o sexo.')).not.toBeInTheDocument();
  });
});
