import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get } = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { get },
}));

import { obterShapesMunicipios } from '@/modules/territorios/territorios-service';

describe('territorios-service', () => {
  beforeEach(() => get.mockReset());

  it('carrega os shapes municipais pelo backend da aplicação', async () => {
    const shapes = [
      {
        territorio_id: 10,
        codigo_municipio_ibge: 5208707,
        nome: 'Goiânia',
        cor: '#12AB34',
        quantidade_eleitores: 99999,
        quantidade_pessoas: 125,
        geometry: { type: 'MultiPolygon', coordinates: [] },
      },
    ];
    get.mockResolvedValueOnce({ data: shapes });

    await expect(obterShapesMunicipios()).resolves.toEqual(shapes);
    expect(get).toHaveBeenCalledWith('/api/v1/territorios/mapa/malhas', {
      params: { tipo: 'municipio', territorio_id: undefined },
    });
  });

  it('filtra os shapes municipais por território selecionado', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await expect(obterShapesMunicipios(10)).resolves.toEqual([]);
    expect(get).toHaveBeenCalledWith('/api/v1/territorios/mapa/malhas', {
      params: { tipo: 'municipio', territorio_id: 10 },
    });
  });
});
