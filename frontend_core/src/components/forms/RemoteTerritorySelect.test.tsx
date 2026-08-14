import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

import { RemoteTerritorySelect } from '@/components/forms/RemoteTerritorySelect';
import { listarTerritorios } from '@/modules/territorios/territorios-service';

vi.mock('@/modules/territorios/territorios-service', () => ({
  listarTerritorios: vi.fn(),
}));

function renderSelect() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <RemoteTerritorySelect open />
    </QueryClientProvider>,
  );
}

describe('RemoteTerritorySelect', () => {
  it('pesquisa territórios no backend conforme o usuário digita', async () => {
    vi.mocked(listarTerritorios).mockResolvedValue([
      { id: 10, nome: 'Região Norte' } as Awaited<ReturnType<typeof listarTerritorios>>[number],
    ]);
    renderSelect();

    await waitFor(() => expect(listarTerritorios).toHaveBeenCalledWith(false, undefined));
    expect(await screen.findByText('Região Norte')).toBeInTheDocument();

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'Norte' } });
    await waitFor(() => expect(listarTerritorios).toHaveBeenCalledWith(false, 'Norte'));
  });
});
