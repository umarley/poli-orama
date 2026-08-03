import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import { RemotePersonSelect } from '@/components/forms/RemotePersonSelect';
import { buscarPessoas } from '@/modules/cadastro/pessoas-service';

vi.mock('@/modules/cadastro/pessoas-service', () => ({
  buscarPessoas: vi.fn(),
}));

function renderSelect(props: React.ComponentProps<typeof RemotePersonSelect> = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RemotePersonSelect {...props} />
    </QueryClientProvider>,
  );
}

describe('RemotePersonSelect', () => {
  it('busca pessoas remotamente somente depois do tamanho minimo', async () => {
    vi.mocked(buscarPessoas).mockResolvedValue([]);
    renderSelect();

    const input = screen.getByRole('combobox');
    fireEvent.change(input, { target: { value: 'L' } });
    await new Promise((resolve) => window.setTimeout(resolve, 300));
    expect(buscarPessoas).not.toHaveBeenCalled();

    fireEvent.change(input, { target: { value: 'Luiz' } });
    await waitFor(() => expect(buscarPessoas).toHaveBeenCalledWith('Luiz'));
  });

  it('remove dos resultados as pessoas informadas em excludeIds', async () => {
    vi.mocked(buscarPessoas).mockResolvedValue([
      {
        id: 1258,
        nome_completo: 'LUIZ CARLOS DE FREITAS',
        data_nascimento: null,
        documento: null,
        telefone: null,
      },
      {
        id: 1259,
        nome_completo: 'LUIZ FERNANDO',
        data_nascimento: null,
        documento: null,
        telefone: null,
      },
    ]);
    renderSelect({ excludeIds: [1259] });

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Luiz' } });

    expect(await screen.findByText('LUIZ CARLOS DE FREITAS')).toBeInTheDocument();
    expect(screen.queryByText('LUIZ FERNANDO')).not.toBeInTheDocument();
  });
});
