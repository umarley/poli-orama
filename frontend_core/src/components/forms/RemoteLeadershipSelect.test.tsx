import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import { formatLeadershipLabel } from '@/components/forms/leadership-label';
import { RemoteLeadershipSelect } from '@/components/forms/RemoteLeadershipSelect';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';
import type { Lideranca } from '@/modules/cadastro/types';

vi.mock('@/modules/cadastro/pessoas-service', () => ({
  listarLiderancas: vi.fn(),
}));

function leadership(overrides: Partial<Lideranca> = {}): Lideranca {
  return {
    id: 450,
    tenant_id: 1,
    pessoa_id: 10,
    tipo_lideranca: 'lider',
    coordenador_id: null,
    apelido_campanha: null,
    ativo: true,
    criado_em: '2026-01-01T00:00:00Z',
    atualizado_em: '2026-01-01T00:00:00Z',
    pessoa_nome_completo: 'Maria da Silva',
    ...overrides,
  };
}

function renderSelect() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RemoteLeadershipSelect open />
    </QueryClientProvider>,
  );
}

describe('RemoteLeadershipSelect', () => {
  it('exibe o nome e inclui o apelido preenchido entre parenteses', () => {
    expect(formatLeadershipLabel(leadership({ apelido_campanha: 'Mariazinha' }))).toBe(
      'Maria da Silva (Mariazinha)',
    );
    expect(formatLeadershipLabel(leadership({ apelido_campanha: '   ' }))).toBe('Maria da Silva');
  });

  it('carrega todas as liderancas e pesquisa novamente no banco enquanto o usuario digita', async () => {
    vi.mocked(listarLiderancas).mockResolvedValue([leadership()]);
    renderSelect();

    await waitFor(() => expect(listarLiderancas).toHaveBeenCalledWith({}));
    expect(await screen.findByText('Maria da Silva')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'M' } });
    await waitFor(() => expect(listarLiderancas).toHaveBeenCalledWith({ query: 'M' }));
  });
});
