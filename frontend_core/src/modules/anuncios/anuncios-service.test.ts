import { beforeEach, describe, expect, it, vi } from 'vitest';

const { post } = vi.hoisted(() => ({ post: vi.fn() }));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { post },
}));

import {
  exportOperationalData,
  installPlanningPoint,
  uploadExecutionMedia,
} from './anuncios-service';

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

  it('registra a instalação com idempotência e a fotografia principal', async () => {
    const photo = new File(['foto'], 'instalacao.jpg', { type: 'image/jpeg' });
    const payload = {
      chave_idempotencia: 'execution-123',
      latitude: -12.9714,
      longitude: -38.5014,
      capturado_em: '2026-09-26T15:00:00.000Z',
      materiais: [{ material_id: 8, quantidade: 2 }],
    };
    post.mockResolvedValueOnce({ data: { execucao: { uuid_publico: 'execution-uuid' } } });

    await installPlanningPoint('point-uuid', payload, photo);

    expect(post).toHaveBeenCalledOnce();
    const [url, body, options] = post.mock.calls[0];
    expect(url).toBe('/api/v1/anuncios/app/pontos/point-uuid/instalar');
    expect(body).toBeInstanceOf(FormData);
    expect((body as FormData).get('dados')).toBe(JSON.stringify(payload));
    expect((body as FormData).get('foto')).toBe(photo);
    expect(options).toEqual({ headers: { 'Idempotency-Key': 'execution-123' } });
  });

  it('anexa cada evidência à execução criada', async () => {
    const video = new File(['video'], 'evidencia.mp4', { type: 'video/mp4' });
    post.mockResolvedValueOnce({ data: { id: 91 } });

    await uploadExecutionMedia('execution-uuid', video);

    const [url, body, options] = post.mock.calls[0];
    expect(url).toBe('/api/v1/anuncios/app/execucoes/execution-uuid/midias');
    expect((body as FormData).get('arquivo')).toBe(video);
    expect(options).toEqual({ timeout: 120_000 });
  });
});
