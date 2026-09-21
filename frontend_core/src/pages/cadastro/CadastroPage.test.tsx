import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useSessionStore } from '@/stores/session-store';

const services = vi.hoisted(() => ({
  listPeople: vi.fn(),
  listPersonTypes: vi.fn(),
  listMaritalStatuses: vi.fn(),
  listLeaderships: vi.fn(),
  listTags: vi.fn(),
  deactivatePerson: vi.fn(),
}));

vi.mock('@/modules/cadastro/pessoas-service', () => ({
  listarPessoas: services.listPeople,
  listarTiposPessoa: services.listPersonTypes,
  listarEstadosCivis: services.listMaritalStatuses,
  listarLiderancas: services.listLeaderships,
  listarTags: services.listTags,
  inativarPessoa: services.deactivatePerson,
}));

vi.mock('@/components/layout/PageHeader', () => ({
  PageHeader: ({ actions }: { actions?: ReactNode }) => <div>{actions}</div>,
}));

vi.mock('@/components/territorios/TerritorySelect', () => ({
  TerritorySelect: () => <div data-testid="territory-select" />,
}));

vi.mock('@/components/data/BaseTable', () => ({
  BaseTable: ({
    dataSource,
    locale,
  }: {
    dataSource?: unknown[];
    locale?: { emptyText?: ReactNode };
  }) => <div>{dataSource?.length ? `${dataSource.length} resultado(s)` : locale?.emptyText}</div>,
}));

vi.mock('./PessoaWizard', () => ({ PessoaWizard: () => null }));

import { CadastroPage } from './CadastroPage';

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>
        <CadastroPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function setProfile(profile: string) {
  useSessionStore.setState({
    user: {
      id: 1,
      name: 'Usuário de teste',
      email: 'teste@example.com',
      initials: 'UT',
      role: profile,
      profiles: [profile],
      permissions: ['cadastro.visualizar', 'cadastro.criar', 'cadastro.editar'],
      liderancaId: null,
      mustChangePassword: false,
      mfaEnabled: false,
    },
  });
}

describe('CadastroPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    services.listPeople.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 });
    services.listPersonTypes.mockResolvedValue([]);
    services.listMaritalStatuses.mockResolvedValue([]);
    services.listLeaderships.mockResolvedValue([]);
    services.listTags.mockResolvedValue([]);
  });

  it('não carrega a listagem inicial para telefonista e exige uma busca válida', async () => {
    setProfile('telefonista');
    renderPage();

    expect(
      screen.getByText('Utilize os filtros acima para localizar uma pessoa ou eleitor.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Nova pessoa/ })).toBeInTheDocument();
    expect(services.listPeople).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: 'Filtrar' }));
    expect(
      await screen.findByText(
        'Informe ao menos dois caracteres ou selecione um filtro para pesquisar.',
      ),
    ).toBeInTheDocument();
    expect(services.listPeople).not.toHaveBeenCalled();

    fireEvent.change(screen.getByPlaceholderText('Nome, documento ou telefone'), {
      target: { value: 'Maria' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Filtrar' }));

    await waitFor(() =>
      expect(services.listPeople).toHaveBeenCalledWith({
        query: 'Maria',
        page: 1,
        page_size: 10,
      }),
    );
    expect(
      await screen.findByText('Nenhum cadastro encontrado para os critérios informados.'),
    ).toBeInTheDocument();
  });

  it('mantém a listagem inicial para os demais perfis', async () => {
    setProfile('gestor');
    renderPage();

    await waitFor(() =>
      expect(services.listPeople).toHaveBeenCalledWith({ page: 1, page_size: 10 }),
    );
  });
});
