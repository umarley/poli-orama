import { beforeEach, describe, expect, it, vi } from 'vitest';

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { post },
}));

import { exportOperationalData } from './anuncios-service';

describe('anuncios-service', () => {
  beforeEach(() => {
    post.mockReset();
  });

  it('exporta todos os filtros operacionais no formato selecionado', async () => {
    const blob = new Blob(['arquivo']);
    const click = vi.fn();
    const anchor = { click, href: '', download: '' } as unknown as HTMLAnchorElement;
    const createElement = vi.spyOn(document, 'createElement').mockReturnValue(anchor);
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:operacao');
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    post.mockResolvedValueOnce({ data: blob });
    const filters = {
      data_inicio: '2026-09-25',
      data_fim: '2026-09-25',
      equipe_id: 2,
      usuario_id: 3,
      material_id: 4,
      rota_id: 5,
      territorio_id: 6,
      status: 'EM_EXECUCAO',
    };

    await exportOperationalData(filters, 'xlsx');

    expect(post).toHaveBeenCalledWith(
      '/api/v1/anuncios/operacao/exportacoes',
      { ...filters, formato: 'xlsx' },
      { responseType: 'blob', timeout: 60_000 },
    );
    expect(anchor.download).toMatch(/^operacao-anuncios-\d{4}-\d{2}-\d{2}\.xlsx$/);
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:operacao');

    createElement.mockRestore();
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });
});
